# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import os
import pathlib
from secrets import token_hex

import boto3
import pytest
import pytest_asyncio
from botocore.config import Config as BotoConfig
from juju.application import Application
from juju.model import Model
from minio import Minio
from ops import JujuVersion
from pytest import Config, FixtureRequest
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import inject_charm_config, inject_venv

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

import nest_asyncio

nest_asyncio.apply()


@pytest.fixture(autouse=True)
def skip_by_juju_version(request, model):
    """Skip the test if juju version is lower then the `skip_juju_version` marker value."""
    if request.node.get_closest_marker("skip_juju_version"):
        current_version = JujuVersion(
            f"{model.info.agent_version.major}.{model.info.agent_version.minor}.{model.info.agent_version.patch}"
        )
        min_version = JujuVersion(request.node.get_closest_marker("skip_juju_version").args[0])
        if current_version < min_version:
            pytest.skip("Juju version is too old")


def pytest_configure(config):
    """Add new marker."""
    config.addinivalue_line(
        "markers",
        "skip_juju_version(version): skip test if Juju version is lower than version",
    )


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/flask")


@pytest.fixture(scope="module", name="test_tracing_flask_image")
def fixture_test_tracing_flask_image(pytestconfig: Config):
    """Return the --test-flask-tracing-image test parameter."""
    test_flask_image = pytestconfig.getoption("--test-tracing-flask-image")
    if not test_flask_image:
        raise ValueError("the following arguments are required: --test-tracing-flask-image")
    return test_flask_image


@pytest.fixture(scope="module", name="django_tracing_app_image")
def fixture_django_tracing_app_image(pytestconfig: Config):
    """Return the --django-tracing-app-image test parameter."""
    image = pytestconfig.getoption("--django-tracing-app-image")
    if not image:
        raise ValueError("the following arguments are required: --django-tracing-app-image")
    return image


@pytest.fixture(scope="module", name="fastapi_tracing_app_image")
def fixture_fastapi_tracing_app_image(pytestconfig: Config):
    """Return the --fastapi-tracing-app-image test parameter."""
    image = pytestconfig.getoption("--fastapi-tracing-app-image")
    if not image:
        raise ValueError("the following arguments are required: --fastapi-tracing-app-image")
    return image


@pytest.fixture(scope="module", name="go_tracing_app_image")
def fixture_go_tracing_app_image(pytestconfig: Config):
    """Return the --go-tracing-app-image test parameter."""
    image = pytestconfig.getoption("--go-tracing-app-image")
    if not image:
        raise ValueError("the following arguments are required: --go-tracing-app-image")
    return image


async def build_charm_file(
    pytestconfig: pytest.Config, ops_test: OpsTest, tmp_path_factory, framework
) -> str:
    """Get the existing charm file if exists, build a new one if not."""
    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"/{framework}-k8s" in f), None
    )

    if not charm_file:
        charm_location = PROJECT_ROOT / f"examples/{framework}/charm"
        if framework == "flask":
            charm_location = PROJECT_ROOT / f"examples/{framework}"
        charm_file = await ops_test.build_charm(charm_location)
    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    return pathlib.Path(charm_file).absolute()


@pytest_asyncio.fixture(scope="module", name="flask_tracing_app")
async def flask_tracing_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    test_tracing_flask_image: str,
):
    """Build and deploy the flask charm with test-tracing-flask image."""
    app_name = "flask-tracing-k8s"

    resources = {
        "flask-app-image": test_tracing_flask_image,
    }
    charm_file = await build_charm_file(pytestconfig, ops_test, tmp_path_factory, "flask")
    app = await model.deploy(
        charm_file, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle(raise_on_blocked=True)
    return app


@pytest_asyncio.fixture(scope="module", name="django_tracing_app")
async def django_tracing_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    django_tracing_app_image: str,
):
    """Build and deploy the Django charm with django-tracing-app image."""
    app_name = "django-tracing-k8s"

    resources = {
        "django-app-image": django_tracing_app_image,
    }
    charm_file = await build_charm_file(pytestconfig, ops_test, tmp_path_factory, "django")

    app = await model.deploy(
        charm_file,
        resources=resources,
        config={"django-allowed-hosts": "*"},
        application_name=app_name,
        series="jammy",
    )
    # await model.wait_for_idle(raise_on_blocked=True)
    return app


@pytest_asyncio.fixture(scope="module", name="fastapi_tracing_app")
async def fastapi_tracing_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    fastapi_tracing_app_image: str,
):
    """Build and deploy the FastAPI charm with fastapi-tracing-app image."""
    app_name = "fastapi-tracing-k8s"

    resources = {
        "app-image": fastapi_tracing_app_image,
    }
    charm_file = await build_charm_file(pytestconfig, ops_test, tmp_path_factory, "fastapi")
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    # await model.wait_for_idle(raise_on_blocked=True)
    return app


@pytest_asyncio.fixture(scope="module", name="go_tracing_app")
async def go_tracing_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    go_tracing_app_image: str,
):
    """Build and deploy the Go charm with go-tracing-app image."""
    app_name = "go-tracing-k8s"

    resources = {
        "app-image": go_tracing_app_image,
    }
    charm_file = await build_charm_file(pytestconfig, ops_test, tmp_path_factory, "go")
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    # await model.wait_for_idle(raise_on_blocked=True)
    return app


async def deploy_and_configure_minio(ops_test: OpsTest, get_unit_ips) -> None:
    """Deploy and set up minio and s3-integrator needed for s3-like storage backend in the HA charms."""
    config = {
        "access-key": "accesskey",
        "secret-key": "secretkey",
    }
    minio_app = await ops_test.model.deploy("minio", channel="edge", trust=True, config=config)
    await ops_test.model.wait_for_idle(
        apps=[minio_app.name], status="active", timeout=2000, idle_period=45
    )
    minio_addr = (await get_unit_ips(minio_app.name))[0]

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
    s3_integrator_app: Application = ops_test.model.applications["s3-integrator"]
    s3_integrator_leader: Unit = s3_integrator_app.units[0]

    await s3_integrator_app.set_config(
        {
            "endpoint": f"minio-0.minio-endpoints.{ops_test.model.name}.svc.cluster.local:9000",
            "bucket": "tempo",
        }
    )

    action = await s3_integrator_leader.run_action("sync-s3-credentials", **config)
    action_result = await action.wait()
    assert action_result.status == "completed"


@pytest_asyncio.fixture(scope="module", name="tempo_app")
async def deploy_tempo_cluster(ops_test: OpsTest, get_unit_ips):
    """Deploys tempo in its HA version together with minio and s3-integrator."""
    tempo_app = "tempo"
    worker_app = "tempo-worker"
    tempo_worker_charm_url, worker_channel = "tempo-worker-k8s", "edge"
    tempo_coordinator_charm_url, coordinator_channel = "tempo-coordinator-k8s", "edge"
    await ops_test.model.deploy(
        tempo_worker_charm_url, application_name=worker_app, channel=worker_channel, trust=True
    )
    app = await ops_test.model.deploy(
        tempo_coordinator_charm_url,
        application_name=tempo_app,
        channel=coordinator_channel,
        trust=True,
    )
    await ops_test.model.deploy("s3-integrator", channel="edge")

    await ops_test.model.integrate(tempo_app + ":s3", "s3-integrator" + ":s3-credentials")
    await ops_test.model.integrate(tempo_app + ":tempo-cluster", worker_app + ":tempo-cluster")

    await deploy_and_configure_minio(ops_test, get_unit_ips)
    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(
            apps=[tempo_app, worker_app, "s3-integrator"],
            status="active",
            timeout=2000,
            idle_period=30,
            # TODO: remove when https://github.com/canonical/tempo-coordinator-k8s-operator/issues/90 is fixed
            raise_on_error=False,
        )
    return app
