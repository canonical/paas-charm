# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import collections
import logging
import pathlib
import time
from secrets import token_hex
from typing import cast

import jubilant
import kubernetes
import pytest
from minio import Minio

from tests.integration.conftest import deploy_postgresql, generate_app_fixture
from tests.integration.helpers import jubilant_temp_controller
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="flask_app")
def flask_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    tmp_path_factory,
):
    framework = "flask"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=False,
        resources={
            "flask-app-image": pytestconfig.getoption(f"--test-{framework}-image"),
        },
    )


@pytest.fixture(scope="module", name="flask_minimal_app")
def flask_minimal_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
    framework = "flask-minimal"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=False,
        resources={
            "flask-app-image": pytestconfig.getoption(f"--{framework}-app-image"),
        },
    )


@pytest.fixture(scope="module", name="django_app")
def django_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
    framework = "django"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        config={"django-allowed-hosts": "*"},
        resources={
            "django-app-image": pytestconfig.getoption(f"--{framework}-app-image"),
        },
    )


@pytest.fixture(scope="module", name="fastapi_app")
def fastapi_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
    framework = "fastapi"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        config={"non-optional-string": "string"},
    )


@pytest.fixture(scope="module", name="go_app")
def go_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
    framework = "go"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        config={"metrics-port": 8081},
    )


@pytest.fixture(scope="module", name="expressjs_app")
def expressjs_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
    framework = "expressjs"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
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

    juju.wait(lambda status: status.apps[minio_app_name].is_active, timeout=2000)
    return App(minio_app_name)


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
    tempo_worker_charm_url, worker_channel = "tempo-worker-k8s", "edge"
    tempo_coordinator_charm_url, coordinator_channel = "tempo-coordinator-k8s", "edge"
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
    v1.create_namespaced_pod(namespace=namespace, body=pod)
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
    v1.create_namespaced_service(namespace=namespace, body=service)
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
        juju.deploy(loki_app_name, channel="latest/stable", trust=True)
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
    juju.integrate(openfga_server_app.name, "postgresql-k8s")
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
def deploy_rabbitmq_server_fixture(juju: jubilant.Juju, lxd_controller, lxd_model) -> str:
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
