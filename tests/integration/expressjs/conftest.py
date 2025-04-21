# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""
import collections
import logging
import pathlib
import subprocess  # nosec B404
import time
from collections.abc import Generator
from typing import Any, Dict, cast

import jubilant
import kubernetes
import pytest
from minio import Minio

from tests.integration.helpers import inject_venv
from tests.integration.types import App

logger = logging.getLogger(__name__)

import os

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

import pathlib


@pytest.fixture(scope="session")
def charm_file(metadata: Dict[str, Any], pytestconfig: pytest.Config):
    """Pytest fixture that packs the charm and returns the filename, or --charm-file if set."""
    charm_file = pytestconfig.getoption("--charm-file")
    if charm_file:
        yield charm_file
        return

    try:
        subprocess.run(
            ["charmcraft", "pack"], check=True, capture_output=True, text=True
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    app_name = metadata["name"]
    charm_path = pathlib.Path(__file__).parent.parent.parent
    charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name} .charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    yield str(charms[0])


@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    def show_debug_log(juju: jubilant.Juju):
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return


def build_charm_file(pytestconfig: pytest.Config, framework) -> str:
    """Get the existing charm file if exists, build a new one if not."""
    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"/{framework}-k8s" in f), None
    )

    if not charm_file:
        charm_location = PROJECT_ROOT / f"examples/{framework}/charm"
        if framework == "flask":
            charm_location = PROJECT_ROOT / f"examples/{framework}"
        try:
            subprocess.run(
                ["charmcraft", "pack", "--project-dir", charm_location],
                check=True,
                capture_output=True,
                text=True,
            )  # nosec B603, B607

            app_name = "expressjs-k8s"
            charm_path = pathlib.Path(__file__).parent.parent.parent.parent
            charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
            assert charms, f"{app_name} .charm file not found"
            assert (
                len(charms) == 1
            ), f"{app_name} has more than one .charm file, unsure which to use"
            charm_file = str(charms[0])
        except subprocess.CalledProcessError as exc:
            raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    return pathlib.Path(charm_file).absolute()


@pytest.mark.skip_juju_version("3.4")
@pytest.fixture(scope="module", name="expressjs_app")
def expressjs_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
):
    # pylint: disable=too-many-locals
    """Discourse charm used for integration testing.
    Builds the charm and deploys it and the relations it depends on.
    """
    app_name = "expressjs-k8s"

    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield App(app_name)
        return

    juju.deploy(
        "postgresql-k8s",
        channel="14/stable",
        base="ubuntu@22.04",
        revision=300,
        trust=True,
        config={"profile": "testing"},
    )
    juju.wait(
        lambda status: jubilant.all_active(status, ["postgresql-k8s"]),
        timeout=20 * 60,
    )

    resources = {
        "app-image": pytestconfig.getoption("--expressjs-app-image"),
    }
    charm_file = build_charm_file(pytestconfig, "expressjs")
    juju.deploy(
        charm=charm_file,
        resources=resources,
    )

    juju.wait(lambda status: jubilant.all_waiting(status, [app_name]))

    # configure postgres
    juju.config(
        "postgresql-k8s",
        {
            "plugin_hstore_enable": "true",
            "plugin_pg_trgm_enable": "true",
        },
    )
    juju.wait(lambda status: jubilant.all_active(status, ["postgresql-k8s"]))

    # Add required relations
    status = juju.status()
    assert status.apps[app_name].units[app_name + "/0"].is_waiting
    juju.integrate(app_name, "postgresql-k8s:database")
    juju.wait(jubilant.all_active)

    yield App(app_name)


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/expressjs")

def deploy_and_configure_minio(
    juju: jubilant.Juju,
) -> None:
    """Deploy and set up minio and s3-integrator needed for s3-like storage backend in the HA charms."""
    config = {
        "access-key": "accesskey",
        "secret-key": "secretkey",
    }
    minio_app_name = "minio"
    juju.deploy(
        minio_app_name,
        channel="edge",
        config=config,
        trust=True,
    )

    juju.wait(lambda status: status.apps[minio_app_name].is_active, timeout=2000)
    status = juju.status()
    minio_addr = status.apps[minio_app_name].units[minio_app_name + "/0"].address

    mc_client = Minio(
        f"{minio_addr}:9000",
        access_key="accesskey",
        secret_key="secretkey",
        secure=False,
    )

    # create tempo bucket
    found = mc_client.bucket_exists("tempo")
    if not found:
        mc_client.make_bucket("tempo")

    # configure s3-integrator
    juju.config(
        "s3-integrator",
        {
            "endpoint": f"minio-0.minio-endpoints.{juju.status().model.name}.svc.cluster.local:9000",
            "bucket": "tempo",
        },
    )

    task = juju.run("s3-integrator/0", "sync-s3-credentials", config)
    assert task.status == "completed"


@pytest.fixture(scope="module", name="tempo_app")
def deploy_tempo_cluster(
    juju: jubilant.Juju,
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
    juju.deploy(
        "s3-integrator",
        channel="edge",
    )
    juju.integrate(tempo_app + ":s3", "s3-integrator" + ":s3-credentials")
    juju.integrate(tempo_app + ":tempo-cluster", worker_app + ":tempo-cluster")
    deploy_and_configure_minio(juju)

    juju.wait(
        lambda status: jubilant.all_active(status, [tempo_app, worker_app, "s3-integrator"]),
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
