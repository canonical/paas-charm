# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import collections
import contextlib
import logging
import pathlib
import subprocess
import sys
import time
from secrets import token_hex
from typing import cast

import jubilant
import kubernetes
import pytest
import urllib3.util.connection
from lightkube import Client
from lightkube.generic_resource import create_namespaced_resource
from lightkube.resources.core_v1 import Service
from minio import Minio
from tenacity import retry, stop_after_attempt, wait_fixed

from tests.integration.conftest import deploy_postgresql, generate_app_fixture
from tests.integration.helpers import jubilant_temp_controller
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
HOSTNAME = "gateway.internal"

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="ingress_provider")
def ingress_provider_fixture(
    juju: jubilant.Juju,
):
    juju.deploy(
        charm="gateway-api-integrator",
        app="gateway",
        channel="latest/edge",
        trust=True,
        config={"gateway-class": "ck-gateway"},
    )
    juju.deploy(
        charm="ingress-configurator",
        app="configurator",
        channel="latest/edge",
        trust=True,
        config={"hostname": HOSTNAME},
    )
    juju.deploy(
        charm="self-signed-certificates",
        app="cert",
        channel="1/edge",
    )
    juju.integrate("cert:certificates", "gateway:certificates")
    juju.integrate("configurator:gateway-route", "gateway:gateway-route")

    juju.wait(
        # gateway/configurator can be blocked before the app-ingress relation is created.
        lambda status: jubilant.all_active(status, "cert"),
        timeout=10 * 60,
    )
    return ("gateway", "configurator")


def gateway_lb_ip(juju: jubilant.Juju, ingress_provider: tuple[str, str]) -> str:
    gateway_resource = create_namespaced_resource(
        group="gateway.networking.k8s.io",
        version="v1",
        kind="Gateway",
        plural="gateways",
    )

    @retry(stop=stop_after_attempt(12), wait=wait_fixed(5))
    def _gateway_lb_ip() -> str:
        gateway_app, _ = ingress_provider
        model_name = juju.status().model.name
        client = Client()
        service = client.get(Service, name=gateway_app, namespace=model_name)
        if (
            service.status
            and service.status.loadBalancer
            and service.status.loadBalancer.ingress
            and service.status.loadBalancer.ingress[0].ip
        ):
            return service.status.loadBalancer.ingress[0].ip

        gateway = client.get(gateway_resource, name=gateway_app, namespace=model_name)
        gateway_status = getattr(gateway, "status", None)
        if isinstance(gateway_status, dict):
            addresses = gateway_status.get("addresses")
        else:
            addresses = getattr(gateway_status, "addresses", None)
        if not addresses:
            raise ValueError(f"No addresses in Gateway status for resource {gateway_app!r}")
        if isinstance(addresses[0], dict):
            address_value = addresses[0].get("value")
        else:
            address_value = getattr(addresses[0], "value", None)
        if not address_value:
            raise ValueError(f"No Gateway address value set for resource {gateway_app!r}")
        return address_value

    return _gateway_lb_ip()


@pytest.fixture(scope="module", name="flask_minimal_app")
def flask_minimal_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    flask_minimal_app_image: str,
    tmp_path_factory,
):
    framework = "flask-minimal"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=False,
        resources={
            "app-image": flask_minimal_app_image,
        },
    )


@pytest.fixture(scope="module", name="fastapi_app")
def fastapi_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    fastapi_app_image: str,
    tmp_path_factory,
):
    framework = "fastapi"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": fastapi_app_image,
        },
        config={"non-optional-string": "string"},
    )


@pytest.fixture(scope="module", name="go_app")
def go_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    go_app_image: str,
    tmp_path_factory,
):
    framework = "go"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": go_app_image,
        },
        config={"metrics-port": 8081},
    )


@pytest.fixture(scope="module", name="expressjs_app")
def expressjs_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    expressjs_app_image: str,
    tmp_path_factory,
):
    framework = "expressjs"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": expressjs_app_image,
        },
    )


@pytest.fixture(scope="module", name="minio_app_name")
def minio_app_name_fixture() -> str:
    return "minio"


@pytest.fixture(scope="module", name="s3_credentials")
def s3_credentials_fixture(
    juju: jubilant.Juju,
):
    return {
        "access-key": token_hex(16),
        "secret-key": token_hex(16),
    }


@pytest.fixture(scope="module", name="s3_configuration")
def s3_configuration_fixture(minio_app_name: str) -> dict:
    """Return the S3 configuration to use for media

    Returns:
        The S3 configuration as a dict
    """
    return {
        "bucket": "paas-bucket",
        "path": "/path",
        "region": "us-east-1",
        "s3-uri-style": "path",
        "endpoint": f"http://{minio_app_name}-0.{minio_app_name}-endpoints:9000",
    }


@pytest.fixture(scope="module", name="minio_app")
def minio_app_fixture(juju: jubilant.Juju, minio_app_name, s3_credentials):
    """Deploy and set up minio and s3-integrator needed for s3-like storage backend in the HA charms."""
    config = s3_credentials
    juju.deploy(
        minio_app_name,
        channel="edge",
        config=config,
        trust=True,
    )

    juju.wait(lambda status: status.apps[minio_app_name].is_active, timeout=60 * 30)
    return App(minio_app_name)


@pytest.fixture(scope="module", name="redis_app_name")
def redis_app_name_fixture() -> str:
    return "redis-k8s"


@pytest.fixture(scope="module", name="redis_app")
def redis_app_fixture(juju: jubilant.Juju, redis_app_name):
    """Deploy and set up Redis."""
    juju.deploy(
        redis_app_name,
        channel="latest/edge",
        trust=True,
    )
    juju.wait(lambda status: status.apps[redis_app_name].is_active, timeout=60 * 30)

    return App(redis_app_name)


@pytest.fixture(scope="module", name="valkey_app_name")
def valkey_app_name_fixture() -> str:
    return "valkey"


@pytest.fixture(scope="module", name="valkey_app")
def valkey_app_fixture(juju: jubilant.Juju, valkey_app_name):
    """Deploy and set up Valkey."""
    juju.deploy(
        valkey_app_name,
        channel="9/edge",
        trust=True,
    )
    juju.wait(lambda status: status.apps[valkey_app_name].is_active, timeout=60 * 30)

    return App(valkey_app_name)


@pytest.fixture(scope="module", name="mongodb_app_name")
def mongodb_app_name_fixture() -> str:
    return "mongodb-k8s"


@pytest.fixture(scope="module", name="mongodb_app")
def mongodb_app_fixture(juju: jubilant.Juju, mongodb_app_name):
    """Deploy and set up Redis."""
    juju.deploy(
        mongodb_app_name,
        channel="6/beta",
        revision=61,
        trust=True,
    )

    return App(mongodb_app_name)


@pytest.fixture(scope="module", name="mysql_app_name")
def mysql_app_name_fixture() -> str:
    return "mysql-k8s"


@pytest.fixture(scope="module", name="mysql_app")
def mysql_app_fixture(juju: jubilant.Juju, mysql_app_name):
    """Deploy and set up Redis."""
    if not juju.status().apps.get(mysql_app_name):
        juju.deploy(
            mysql_app_name,
            channel="8.0/stable",
            revision=140,
            trust=True,
        )

    return App(mysql_app_name)


@pytest.fixture(scope="module", name="s3_integrator_app")
def s3_integrator_app_fixture(juju: jubilant.Juju, minio_app, s3_credentials, s3_configuration):
    s3_integrator = "s3-integrator"
    juju.deploy(
        s3_integrator,
        channel="edge",
    )
    juju.wait(
        lambda status: jubilant.all_blocked(status, s3_integrator),
        timeout=120,
    )
    status = juju.status()
    minio_addr = status.apps[minio_app.name].units[minio_app.name + "/0"].address

    mc_client = Minio(
        f"{minio_addr}:9000",
        access_key=s3_credentials["access-key"],
        secret_key=s3_credentials["secret-key"],
        secure=False,
    )

    # create tempo bucket
    bucket_name = s3_configuration["bucket"]
    found = mc_client.bucket_exists(bucket_name)
    if not found:
        mc_client.make_bucket(bucket_name)

    # configure s3-integrator
    juju.config(
        "s3-integrator",
        s3_configuration,
    )

    task = juju.run(f"{s3_integrator}/0", "sync-s3-credentials", s3_credentials)
    assert task.status == "completed"
    return App(s3_integrator)


@pytest.fixture(scope="module", name="tempo_app")
def tempo_app_fixture(
    juju: jubilant.Juju,
    s3_integrator_app,
):
    """Deploys tempo in its HA version together with minio and s3-integrator."""
    tempo_app = "tempo"
    worker_app = "tempo-worker"
    tempo_worker_charm_url, worker_channel = "tempo-worker-k8s", "2/edge"
    tempo_coordinator_charm_url, coordinator_channel = "tempo-coordinator-k8s", "2/edge"
    juju.deploy(
        tempo_worker_charm_url,
        app=worker_app,
        channel=worker_channel,
        trust=True,
    )
    juju.deploy(
        tempo_coordinator_charm_url,
        app=tempo_app,
        channel=coordinator_channel,
        trust=True,
    )
    juju.integrate(f"{tempo_app}:s3", f"{s3_integrator_app.name}:s3-credentials")
    juju.integrate(f"{tempo_app}:tempo-cluster", f"{worker_app}:tempo-cluster")

    return App(tempo_app)


@pytest.fixture(scope="module", name="load_kube_config")
def load_kube_config_fixture(pytestconfig: pytest.Config):
    """Load kubernetes config file."""
    kube_config = pytestconfig.getoption("--kube-config")
    kubernetes.config.load_kube_config(config_file=kube_config)


@pytest.fixture(scope="module")
def mailcatcher(load_kube_config, juju):
    """Deploy test mailcatcher service."""
    namespace = juju.status().model.name
    v1 = kubernetes.client.CoreV1Api()
    pod = kubernetes.client.V1Pod(
        api_version="v1",
        kind="Pod",
        metadata=kubernetes.client.V1ObjectMeta(
            name="mailcatcher",
            namespace=namespace,
            labels={"app.kubernetes.io/name": "mailcatcher"},
        ),
        spec=kubernetes.client.V1PodSpec(
            containers=[
                kubernetes.client.V1Container(
                    name="mailcatcher",
                    image="sj26/mailcatcher",
                    ports=[
                        kubernetes.client.V1ContainerPort(container_port=1025),
                        kubernetes.client.V1ContainerPort(container_port=1080),
                    ],
                )
            ],
        ),
    )

    service = kubernetes.client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=kubernetes.client.V1ObjectMeta(name="mailcatcher-service", namespace=namespace),
        spec=kubernetes.client.V1ServiceSpec(
            type="ClusterIP",
            ports=[
                kubernetes.client.V1ServicePort(port=1025, target_port=1025, name="tcp-1025"),
                kubernetes.client.V1ServicePort(port=1080, target_port=1080, name="tcp-1080"),
            ],
            selector={"app.kubernetes.io/name": "mailcatcher"},
        ),
    )
    try:
        v1.create_namespaced_pod(namespace=namespace, body=pod)
        v1.create_namespaced_service(namespace=namespace, body=service)
    except kubernetes.client.ApiException as e:
        if e.status != 409:
            raise
        logger.info("mailcatcher pod already exists")
    deadline = time.time() + 300
    pod_ip = None
    while True:
        if time.time() > deadline:
            raise TimeoutError("timeout while waiting for mailcatcher pod")
        try:
            pod = v1.read_namespaced_pod(name="mailcatcher", namespace=namespace)
            if pod.status.phase == "Running":
                logger.info("mailcatcher running at %s", pod.status.pod_ip)
                pod_ip = pod.status.pod_ip
                break
        except kubernetes.client.ApiException:
            pass
        logger.info("waiting for mailcatcher pod")
        time.sleep(1)
    SmtpCredential = collections.namedtuple("SmtpCredential", "host port pod_ip")
    return SmtpCredential(
        host=f"mailcatcher-service.{namespace}.svc.cluster.local",
        port=1025,
        pod_ip=pod_ip,
    )


@pytest.fixture(scope="module", name="prometheus_app_name")
def prometheus_app_name_fixture() -> str:
    """Return the name of the prometheus application deployed for tests."""
    return "prometheus-k8s"


@pytest.fixture(scope="module", name="prometheus_app")
def deploy_prometheus_fixture(
    juju: jubilant.Juju,
    prometheus_app_name: str,
) -> App:
    """Deploy prometheus."""
    if not juju.status().apps.get(prometheus_app_name):
        juju.deploy(
            prometheus_app_name,
            channel="1/stable",
            revision=129,
            base="ubuntu@20.04",
            trust=True,
        )
    juju.wait(
        lambda status: status.apps[prometheus_app_name].is_active,
        error=jubilant.any_blocked,
        timeout=6 * 60,
    )
    return App(prometheus_app_name)


@pytest.fixture(scope="module", name="loki_app")
def deploy_loki_fixture(
    juju: jubilant.Juju,
    loki_app_name: str,
) -> App:
    """Deploy loki."""
    if not juju.status().apps.get(loki_app_name):
        juju.deploy(loki_app_name, channel="1/stable", trust=True)
    juju.wait(
        lambda status: status.apps[loki_app_name].is_active,
        error=jubilant.any_blocked,
    )
    return App(loki_app_name)


@pytest.fixture(scope="module", name="cos_apps")
def deploy_cos_fixture(
    juju: jubilant.Juju,
    loki_app,
    prometheus_app,
    grafana_app_name: str,
) -> dict[str:App]:
    """Deploy the cos applications."""
    if not juju.status().apps.get(grafana_app_name):
        juju.deploy(
            grafana_app_name,
            channel="1/stable",
            revision=82,
            base="ubuntu@20.04",
            trust=True,
        )
        juju.wait(
            lambda status: jubilant.all_active(
                status, loki_app.name, prometheus_app.name, grafana_app_name
            )
        )
        juju.integrate(
            f"{prometheus_app.name}:grafana-source",
            f"{grafana_app_name}:grafana-source",
        )
        juju.integrate(
            f"{loki_app.name}:grafana-source",
            f"{grafana_app_name}:grafana-source",
        )
    return {
        "loki_app": loki_app,
        "prometheus_app": prometheus_app,
        "grafana_app": App(grafana_app_name),
    }


@pytest.fixture(scope="module", name="openfga_server_app")
def deploy_openfga_server_fixture(juju: jubilant.Juju) -> App:
    """Deploy openfga k8s charm."""
    openfga_server_app = App("openfga-k8s")
    if juju.status().apps.get(openfga_server_app.name):
        logger.info(f"{openfga_server_app.name} is already deployed")
        return openfga_server_app

    deploy_postgresql(juju)
    juju.deploy(openfga_server_app.name, channel="latest/stable")
    juju.integrate(openfga_server_app.name, "postgresql-k8s:database")
    juju.wait(
        lambda status: jubilant.all_active(status, openfga_server_app.name, "postgresql-k8s"),
        timeout=6 * 60,
    )
    return openfga_server_app


@pytest.fixture(scope="session", name="lxd_controller_name")
def lxd_controller_name_fixture() -> str:
    "Return the controller name for lxd."
    return "localhost"


@pytest.fixture(scope="session", name="lxd_controller")
def lxd_controller(
    juju: jubilant.Juju,
    lxd_controller_name,
) -> str:
    status = juju.status()
    original_controller_name = status.model.controller
    original_model_name = status.model.name
    lxd_cloud_name = "lxd"
    try:
        juju.cli("bootstrap", lxd_cloud_name, lxd_controller_name, include_model=False)
    except jubilant.CLIError as ex:
        if "already exists" not in ex.stderr:
            raise
    finally:
        # Always get back to the original controller and model
        juju.cli(
            "switch", f"{original_controller_name}:{original_model_name}", include_model=False
        )
    yield lxd_controller_name


@pytest.fixture(scope="session", name="lxd_model_name")
def lxd_model_name_fixture(juju: jubilant.Juju) -> str:
    "Return the model name for lxd."
    status = juju.status()
    return status.model.name


@pytest.fixture(scope="session", name="lxd_model")
def lxd_model_fixture(
    request: pytest.FixtureRequest, juju: jubilant.Juju, lxd_controller, lxd_model_name
) -> str:
    "Create the lxd_model and return its name."
    with jubilant_temp_controller(juju, lxd_controller):
        try:
            juju.add_model(lxd_model_name)
        except jubilant.CLIError as ex:
            if "already exists" not in ex.stderr:
                raise
    yield lxd_model_name
    keep_models = cast(bool, request.config.getoption("--keep-models"))
    if not keep_models:
        with jubilant_temp_controller(juju, lxd_controller):
            juju.destroy_model(lxd_model_name, destroy_storage=True, force=True)


@pytest.fixture(scope="session", name="rabbitmq_server_app")
def deploy_rabbitmq_server_fixture(juju: jubilant.Juju, lxd_controller, lxd_model) -> App:
    """Deploy rabbitmq server machine charm."""
    rabbitmq_server_name = "rabbitmq-server"

    with jubilant_temp_controller(juju, lxd_controller, lxd_model):
        if juju.status().apps.get(rabbitmq_server_name):
            logger.info("rabbitmq server already deployed")
            return App(rabbitmq_server_name)

        juju.deploy(
            rabbitmq_server_name,
            channel="edge",
        )

        juju.cli("offer", f"{rabbitmq_server_name}:amqp", include_model=False)
        juju.wait(
            lambda status: jubilant.all_active(status, rabbitmq_server_name),
            timeout=6 * 60,
            delay=10,
        )
    # Add the offer in the original model
    offer_name = f"{lxd_controller}:admin/{lxd_model}.{rabbitmq_server_name}"
    juju.cli("consume", offer_name, include_model=False)
    # The return is a string with the name of the applications, but will not
    # contain the controller or model. Other apps can integrate to rabbitmq using this
    # name as there is a local offer with this name.
    return App(rabbitmq_server_name)


@pytest.fixture(scope="session", name="rabbitmq_server_ha_app")
def deploy_rabbitmq_server_ha_fixture(
    juju: jubilant.Juju, lxd_controller, lxd_model, rabbitmq_server_app
) -> App:
    """Deploy rabbitmq server machine charm in ha mode."""
    with jubilant_temp_controller(juju, lxd_controller, lxd_model):
        juju.add_unit(rabbitmq_server_app.name, num_units=2)
        juju.wait(
            lambda status: jubilant.all_active(status, rabbitmq_server_app.name),
            timeout=6 * 60,
            delay=10,
        )
    return rabbitmq_server_app


@pytest.fixture(scope="module", name="rabbitmq_k8s_app")
def deploy_rabbitmq_k8s_fixture(juju: jubilant.Juju) -> App:
    """Deploy rabbitmq-k8s app."""
    rabbitmq_k8s = App("rabbitmq-k8s")

    if juju.status().apps.get(rabbitmq_k8s.name):
        logger.info(f"{rabbitmq_k8s.name} is already deployed")
        return rabbitmq_k8s

    juju.deploy(
        rabbitmq_k8s.name,
        channel="3.12/edge",
        trust=True,
    )
    juju.wait(
        lambda status: jubilant.all_active(status, rabbitmq_k8s.name),
        timeout=10 * 60,
    )
    return rabbitmq_k8s


@pytest.fixture(scope="module", name="identity_bundle")
def deploy_identity_bundle_fixture(juju: jubilant.Juju):
    """Deploy Canonical identity bundle."""
    if juju.status().apps.get("hydra"):
        logger.info("identity-platform is already deployed")
        return
    juju.deploy("hydra", channel="latest/edge", revision=399, trust=True)
    juju.deploy("kratos", channel="latest/edge", revision=567, trust=True)
    juju.deploy(
        "identity-platform-login-ui-operator", channel="latest/edge", revision=200, trust=True
    )
    juju.deploy("self-signed-certificates", channel="1/stable", revision=317, trust=True)
    juju.deploy("traefik-k8s", "traefik-admin", channel="latest/stable", revision=176, trust=True)
    juju.deploy("traefik-k8s", "traefik-public", channel="latest/edge", revision=270, trust=True)
    deploy_postgresql(juju)
    # Integrations
    juju.integrate(
        "hydra:hydra-endpoint-info", "identity-platform-login-ui-operator:hydra-endpoint-info"
    )
    juju.integrate("hydra:hydra-endpoint-info", "kratos:hydra-endpoint-info")
    juju.integrate("kratos:kratos-info", "identity-platform-login-ui-operator:kratos-info")
    juju.integrate(
        "hydra:ui-endpoint-info", "identity-platform-login-ui-operator:ui-endpoint-info"
    )
    juju.integrate(
        "kratos:ui-endpoint-info", "identity-platform-login-ui-operator:ui-endpoint-info"
    )
    juju.integrate("postgresql-k8s:database", "hydra:pg-database")
    juju.integrate("postgresql-k8s:database", "kratos:pg-database")
    juju.integrate("self-signed-certificates:certificates", "traefik-admin:certificates")
    juju.integrate("self-signed-certificates:certificates", "traefik-public:certificates")
    juju.integrate("traefik-public:traefik-route", "hydra:public-route")
    juju.integrate("traefik-public:traefik-route", "kratos:public-route")
    juju.integrate(
        "traefik-public:traefik-route", "identity-platform-login-ui-operator:public-route"
    )

    juju.config("kratos", {"enforce_mfa": False})


@pytest.fixture(scope="module", name="http_proxy_app")
def http_proxy_configurator_fixture(juju: jubilant.Juju, lxd_controller, lxd_model):
    """Deploy http proxy configurator and squid proxy."""

    squid_proxy = "squid-forward-proxy"
    with jubilant_temp_controller(juju, lxd_controller, lxd_model):
        if juju.status().apps.get(squid_proxy):
            logger.info("squid server already deployed")
        else:
            juju.deploy(
                squid_proxy,
                channel="edge",
                config={"hostname": "proxy.example.com"},
            )

            juju.cli("offer", f"{squid_proxy}:http-proxy", include_model=False)
            juju.wait(
                lambda status: jubilant.all_active(status, squid_proxy),
                timeout=6 * 60,
                delay=10,
            )
    # Add the offer in the original model
    offer_name = f"{lxd_controller}:admin/{lxd_model}.{squid_proxy}"
    juju.cli("consume", offer_name, include_model=False)

    http_proxy_configurator = "http-proxy-configurator"
    if juju.status().apps.get(http_proxy_configurator):
        logger.info("http-proxy-configurator server already deployed")
    else:
        juju.deploy(
            http_proxy_configurator,
            channel="latest/edge",
            config={
                "http-proxy-auth": "none",
                "http-proxy-domains": "www.example.com",
            },
        )
        juju.integrate(http_proxy_configurator, squid_proxy)
    juju.wait(
        lambda status: jubilant.all_active(status, http_proxy_configurator),
        timeout=(5 * 60),
        delay=10,
    )

    return App(http_proxy_configurator)


@pytest.fixture(scope="session")
def browser_context_manager():
    """
    A session-scoped fixture that installs the Playwright browser
    and yields. This ensures the browser is installed only for oauth test.
    """
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("Chromium installation complete.")
    except subprocess.CalledProcessError as e:
        output = e.stderr or e.stdout or str(e)
        pytest.fail(f"Failed to install Playwright browser: {output}")

    yield


@contextlib.contextmanager
def pin_dns(hostname: str, ip: str):
    """Resolve ``hostname`` to ``ip`` for every connection made in the context.

    The gateway only routes by the ingress hostname, which exists solely as a
    Host header in these tests and is not in DNS. Some apps (e.g. the FastAPI
    app with its ``root_path``) reply with a redirect to that hostname, so we
    pin its resolution to the gateway load-balancer IP for both the initial
    request and any connection opened while following redirects.
    """
    original_create_connection = urllib3.util.connection.create_connection

    def patched_create_connection(address, *args, **kwargs):
        host, port = address
        if host == hostname:
            address = (ip, port)
        return original_create_connection(address, *args, **kwargs)

    urllib3.util.connection.create_connection = patched_create_connection
    try:
        yield
    finally:
        urllib3.util.connection.create_connection = original_create_connection


@contextlib.contextmanager
def ingress_relation(juju: jubilant.Juju, app: App, ingress_provider: tuple[str, str]):
    """Relate ``app`` to the ingress configurator, cleaning up on exit.

    configurator:ingress accepts a single relation, so the relation is always
    removed (and the removal awaited) on exit, even on failure, so one failing
    case can't exhaust the quota for the next one.
    """
    gateway_app, configurator_app = ingress_provider
    try:
        juju.integrate(app.name, configurator_app)
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise
    try:
        juju.wait(
            lambda status: jubilant.all_active(status, app.name, gateway_app, configurator_app),
            timeout=10 * 60,
            delay=5,
        )
        yield
    finally:
        juju.remove_relation(app.name, configurator_app)
        juju.wait(
            lambda status: (
                app.name
                not in [
                    rel.related_app
                    for rel in status.apps[configurator_app].relations.get("ingress", [])
                ]
            ),
            timeout=5 * 60,
            delay=5,
        )
