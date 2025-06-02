# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import collections
import logging
import pathlib
import time
from secrets import token_hex

import jubilant
import kubernetes
import pytest
from minio import Minio

from tests.integration.conftest import build_charm_file
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

logger = logging.getLogger(__name__)


def deploy_postgresql(
    juju: jubilant.Juju,
):
    """Deploy and set up postgresql charm needed for the 12-factor charm."""

    if juju.status().apps.get("postgresql-k8s"):
        logger.info("postgresql-k8s already deployed")
        return

    juju.deploy(
        "postgresql-k8s",
        channel="14/stable",
        base="ubuntu@22.04",
        revision=300,
        trust=True,
        config={
            "profile": "testing",
            "plugin_hstore_enable": "true",
            "plugin_pg_trgm_enable": "true",
        },
    )
    juju.wait(
        lambda status: status.apps["postgresql-k8s"].is_active,
        timeout=20 * 60,
    )


@pytest.fixture(scope="module", name="flask_app")
def flask_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
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


def generate_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    framework: str,
    tmp_path_factory,
    image_name: str = "",
    use_postgres: bool = True,
    config: dict[str, str] | None = None,
    resources: dict[str, str] | None = None,
):
    """Generates the charm, configures and deploys it and the relations it depends on."""
    app_name = f"{framework}-k8s"
    if image_name == "":
        image_name = f"{framework}-app-image"
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return App(app_name)
    if resources is None:
        resources = {
            "app-image": pytestconfig.getoption(f"--{image_name}"),
        }
    charm_file = build_charm_file(pytestconfig, framework, tmp_path_factory)
    juju.deploy(
        charm=charm_file,
        resources=resources,
        config=config,
    )

    # Add required relations
    if use_postgres:
        deploy_postgresql(juju)
        juju.integrate(app_name, "postgresql-k8s:database")
        juju.wait(lambda status: status.apps["postgresql-k8s"].is_active, timeout=30 * 60)
    juju.wait(lambda status: status.apps[app_name].is_active, timeout=10 * 60)
    yield App(app_name)


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
        lambda status: jubilant.all_blocked(status, [s3_integrator]),
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

    juju.wait(
        lambda status: jubilant.all_active(
            status, [s3_integrator_app.name, tempo_app, worker_app]
        ),
        timeout=2000,
    )
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
        host=f"mailcatcher-service.{namespace}.svc.cluster.local", port=1025, pod_ip=pod_ip
    )


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
                status, [loki_app.name, prometheus_app.name, grafana_app_name]
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
        lambda status: jubilant.all_active(status, [openfga_server_app.name, "postgresql-k8s"])
    )
    return openfga_server_app
