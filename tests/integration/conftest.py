# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging

import pytest
import pytest_asyncio
from juju.application import Application
from juju.client.jujudata import FileJujuData
from juju.juju import Juju
from juju.model import Controller, Model
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="module", name="ops_test_lxd")
async def ops_test_lxd_fixture(request, tmp_path_factory, ops_test: OpsTest):
    """Return a ops_test fixture for lxd, creating the lxd controller if it does not exist."""
    if not "lxd" in Juju().get_controllers():
        logger.info("bootstrapping lxd")
        _, _, _ = await ops_test.juju("bootstrap", "localhost", "lxd", check=True)

    ops_test = OpsTest(request, tmp_path_factory)
    ops_test.controller_name = "lxd"
    await ops_test._setup_model()
    # The instance is not stored in _instance as that is done for the ops_test fixture
    yield ops_test
    await ops_test._cleanup_models()


@pytest_asyncio.fixture(scope="module", name="lxd_model")
async def lxd_model_fixture(ops_test_lxd: OpsTest) -> Model:
    """Return the current lxd juju model."""
    assert ops_test_lxd.model
    return ops_test_lxd.model


@pytest_asyncio.fixture(scope="module", name="rabbitmq_server_app")  # autouse=True)
async def deploy_rabbitmq_server_fixture(
    lxd_model: Model,
) -> Application:
    """Deploy rabbitmq-server machine app."""
    app = await lxd_model.deploy(
        "rabbitmq-server",
        channel="latest/edge",
    )
    await lxd_model.wait_for_idle(raise_on_blocked=True)
    await lxd_model.create_offer("rabbitmq-server:amqp")
    yield app


@pytest_asyncio.fixture(scope="module", name="rabbitmq_k8s_app")  # autouse=True)
async def deploy_rabbitmq_k8s_fixture(
    model: Model,
) -> Application:
    """Deploy rabbitmq-k8s app."""
    app = await model.deploy(
        "rabbitmq-k8s",
        channel="3.12/edge",
        trust=True,
    )
    await model.wait_for_idle(raise_on_blocked=True)
    yield app


@pytest_asyncio.fixture(scope="module", name="get_unit_ips")
async def fixture_get_unit_ips(ops_test: OpsTest):
    """Return an async function to retrieve unit ip addresses of a certain application."""

    async def get_unit_ips(application_name: str):
        """Retrieve unit ip addresses of a certain application.

        Returns:
            A list containing unit ip addresses.
        """
        _, status, _ = await ops_test.juju("status", "--format", "json")
        status = json.loads(status)
        units = status["applications"][application_name]["units"]
        return tuple(
            unit_status["address"]
            for _, unit_status in sorted(units.items(), key=lambda kv: int(kv[0].split("/")[-1]))
        )

    return get_unit_ips


@pytest_asyncio.fixture(scope="module", name="model")
async def fixture_model(ops_test: OpsTest) -> Model:
    """Return the current testing juju model."""
    assert ops_test.model
    return ops_test.model


@pytest.fixture(scope="module", name="external_hostname")
def external_hostname_fixture() -> str:
    """Return the external hostname for ingress-related tests."""
    return "juju.test"


@pytest.fixture(scope="module", name="traefik_app_name")
def traefik_app_name_fixture() -> str:
    """Return the name of the traefik application deployed for tests."""
    return "traefik-k8s"


@pytest.fixture(scope="module", name="prometheus_app_name")
def prometheus_app_name_fixture() -> str:
    """Return the name of the prometheus application deployed for tests."""
    return "prometheus-k8s"


@pytest.fixture(scope="module", name="loki_app_name")
def loki_app_name_fixture() -> str:
    """Return the name of the prometheus application deployed for tests."""
    return "loki-k8s"


@pytest.fixture(scope="module", name="grafana_app_name")
def grafana_app_name_fixture() -> str:
    """Return the name of the grafana application deployed for tests."""
    return "grafana-k8s"


@pytest_asyncio.fixture(scope="module", name="prometheus_app")
async def deploy_prometheus_fixture(
    model: Model,
    prometheus_app_name: str,
):
    """Deploy prometheus."""
    app = await model.deploy(
        "prometheus-k8s",
        application_name=prometheus_app_name,
        channel="1.0/stable",
        revision=129,
        series="focal",
        trust=True,
    )
    await model.wait_for_idle(raise_on_blocked=True)

    return app


@pytest_asyncio.fixture(scope="module", name="postgresql_k8s")
async def deploy_postgres_fixture(ops_test: OpsTest, model: Model):
    """Deploy postgres k8s charm."""
    _, status, _ = await ops_test.juju("status", "--format", "json")
    version = json.loads(status)["model"]["version"]
    if tuple(map(int, (version.split(".")))) >= (3, 4, 0):
        return await model.deploy("postgresql-k8s", channel="14/stable", trust=True)
    else:
        return await model.deploy("postgresql-k8s", channel="14/stable", revision=300, trust=True)


@pytest_asyncio.fixture(scope="module", name="redis_k8s_app")
async def deploy_redisk8s_fixture(ops_test: OpsTest, model: Model):
    """Deploy Redis k8s charm."""
    redis_app = await model.deploy("redis-k8s", channel="edge")
    await model.wait_for_idle(apps=[redis_app.name], status="active")
    return redis_app


@pytest_asyncio.fixture(scope="function", name="integrate_redis_k8s_flask")
async def integrate_redis_k8s_flask_fixture(
    ops_test: OpsTest, model: Model, flask_app: Application, redis_k8s_app: Application
):
    """Integrate redis_k8s with flask apps."""
    relation = await model.integrate(flask_app.name, redis_k8s_app.name)
    await model.wait_for_idle(apps=[redis_k8s_app.name], status="active")
    yield relation
    await flask_app.destroy_relation("redis", f"{redis_k8s_app.name}")
    await model.wait_for_idle()


@pytest_asyncio.fixture
def run_action(ops_test: OpsTest):
    async def _run_action(application_name, action_name, **params):
        app = ops_test.model.applications[application_name]
        action = await app.units[0].run_action(action_name, **params)
        await action.wait()
        return action.results

    return _run_action
