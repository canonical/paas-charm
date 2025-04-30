# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging
import pathlib

import pytest
import pytest_asyncio
from juju.application import Application
from juju.errors import JujuError
from juju.juju import Juju
from juju.model import Model
from pytest import Config
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import inject_charm_config, inject_venv

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
logger = logging.getLogger(__name__)

NON_OPTIONAL_CONFIGS = {
    "non-optional-bool": {"type": "boolean", "optional": False},
    "non-optional-int": {"type": "int", "optional": False},
}


@pytest.fixture(scope="module", name="test_flask_image")
def fixture_test_flask_image(pytestconfig: Config):
    """Return the --test-flask-image test parameter."""
    test_flask_image = pytestconfig.getoption("--test-flask-image")
    if not test_flask_image:
        raise ValueError("the following arguments are required: --test-flask-image")
    return test_flask_image


@pytest.fixture(scope="module", name="django_app_image")
def fixture_django_app_image(pytestconfig: Config):
    """Return the --django-app-image test parameter."""
    image = pytestconfig.getoption("--django-app-image")
    if not image:
        raise ValueError("the following arguments are required: --django-app-image")
    return image


@pytest.fixture(scope="module", name="fastapi_app_image")
def fixture_fastapi_app_image(pytestconfig: Config):
    """Return the --fastapi-app-image test parameter."""
    image = pytestconfig.getoption("--fastapi-app-image")
    if not image:
        raise ValueError("the following arguments are required: --fastapi-app-image")
    return image


@pytest.fixture(scope="module", name="go_app_image")
def fixture_go_app_image(pytestconfig: Config):
    """Return the --go-app-image test parameter."""
    image = pytestconfig.getoption("--go-app-image")
    if not image:
        raise ValueError("the following arguments are required: --go-app-image")
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


async def build_charm_file_with_config_options(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    framework: str,
    config_options: dict,
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

    charm_file = inject_charm_config(
        charm_file,
        config_options,
        tmp_path_factory.mktemp(framework),
    )
    return pathlib.Path(charm_file).absolute()


@pytest_asyncio.fixture(scope="module", name="flask_app")
async def flask_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    test_flask_image: str,
):
    """Build and deploy the flask charm with test-flask image."""
    app_name = "flask-k8s"

    resources = {
        "flask-app-image": test_flask_image,
    }
    charm_file = await build_charm_file(pytestconfig, ops_test, tmp_path_factory, "flask")
    app = await model.deploy(
        charm_file, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle(apps=[app_name], status="active", timeout=300, raise_on_blocked=True)
    return app


@pytest_asyncio.fixture(scope="module", name="flask_blocked_app")
async def flask_blocked_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    test_flask_image: str,
):
    """Build and deploy the flask charm with test-flask image."""
    app_name = "flask-k8s"

    resources = {
        "flask-app-image": test_flask_image,
    }
    charm_file = await build_charm_file_with_config_options(
        pytestconfig, ops_test, tmp_path_factory, "flask", NON_OPTIONAL_CONFIGS
    )
    app = await model.deploy(
        charm_file, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle(apps=[app_name], status="blocked", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="django_app")
async def django_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    django_app_image: str,
    postgresql_k8s: Application,
):
    """Build and deploy the Django charm with django-app image."""
    app_name = "django-k8s"

    resources = {
        "django-app-image": django_app_image,
    }
    charm_file = await build_charm_file(pytestconfig, ops_test, tmp_path_factory, "django")

    app = await model.deploy(
        charm_file,
        resources=resources,
        config={"django-allowed-hosts": "*"},
        application_name=app_name,
        series="jammy",
    )
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[app_name, postgresql_k8s.name], status="active", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="django_blocked_app")
async def django_blocked_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    django_app_image: str,
    postgresql_k8s: Application,
):
    """Build and deploy the Django charm with django-app image."""
    app_name = "django-k8s"

    resources = {
        "django-app-image": django_app_image,
    }
    charm_file = await build_charm_file_with_config_options(
        pytestconfig, ops_test, tmp_path_factory, "django", NON_OPTIONAL_CONFIGS
    )

    app = await model.deploy(
        charm_file,
        resources=resources,
        config={"django-allowed-hosts": "*"},
        application_name=app_name,
        series="jammy",
    )
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name], status="active", timeout=300)
    await model.wait_for_idle(apps=[app_name], status="blocked", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="fastapi_app")
async def fastapi_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    fastapi_app_image: str,
    postgresql_k8s: Application,
):
    """Build and deploy the FastAPI charm with fastapi-app image."""
    app_name = "fastapi-k8s"

    resources = {
        "app-image": fastapi_app_image,
    }
    charm_file = await build_charm_file(pytestconfig, ops_test, tmp_path_factory, "fastapi")
    app = await model.deploy(
        charm_file,
        resources=resources,
        application_name=app_name,
        config={"non-optional-string": "non-optional-value"},
    )
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[app_name, postgresql_k8s.name], status="active", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="fastapi_blocked_app")
async def fastapi_blocked_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    fastapi_app_image: str,
    postgresql_k8s: Application,
):
    """Build and deploy the FastAPI charm with fastapi-app image."""
    app_name = "fastapi-k8s"

    resources = {"app-image": fastapi_app_image}
    charm_file = await build_charm_file_with_config_options(
        pytestconfig, ops_test, tmp_path_factory, "fastapi", NON_OPTIONAL_CONFIGS
    )
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name], status="active", timeout=300)
    await model.wait_for_idle(apps=[app_name], status="blocked", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="go_app")
async def go_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    go_app_image: str,
    postgresql_k8s,
):
    """Build and deploy the Go charm with go-app image."""
    app_name = "go-k8s"

    resources = {
        "app-image": go_app_image,
    }
    charm_file = await build_charm_file(pytestconfig, ops_test, tmp_path_factory, "go")
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[app_name, postgresql_k8s.name], status="active", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="go_blocked_app")
async def go_blocked_app_fixture(
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
    model: Model,
    go_app_image: str,
    postgresql_k8s,
):
    """Build and deploy the Go charm with go-app image."""
    app_name = "go-k8s"

    resources = {
        "app-image": go_app_image,
    }
    charm_file = await build_charm_file_with_config_options(
        pytestconfig, ops_test, tmp_path_factory, "go", NON_OPTIONAL_CONFIGS
    )
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name], status="active", timeout=300)
    await model.wait_for_idle(apps=[app_name], status="blocked", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="ops_test_lxd")
async def ops_test_lxd_fixture(request, tmp_path_factory, ops_test: OpsTest):
    """Return a ops_test fixture for lxd, creating the lxd controller if it does not exist."""
    if "lxd" not in Juju().get_controllers():
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
    ops_test: OpsTest,
) -> Application:
    """Deploy rabbitmq-server machine app."""
    _, status, _ = await ops_test.juju("status", "--format", "json")
    version = json.loads(status)["model"]["version"]
    if tuple(map(int, (version.split(".")))) >= (3, 4, 0):
        app = await lxd_model.deploy(
            "rabbitmq-server",
            channel="latest/edge",
        )
    else:
        app = await lxd_model.deploy(
            "rabbitmq-server",
            channel="latest/edge",
            series="jammy",
        )

    await lxd_model.wait_for_idle(raise_on_blocked=True)
    await lxd_model.create_offer("rabbitmq-server:amqp")
    yield app


@pytest_asyncio.fixture(scope="module", name="rabbitmq_k8s_app")  # autouse=True)
async def deploy_rabbitmq_k8s_fixture(
    model: Model,
    ops_test: OpsTest,
) -> Application:
    """Deploy rabbitmq-k8s app."""
    _, status, _ = await ops_test.juju("status", "--format", "json")
    version = json.loads(status)["model"]["version"]
    if tuple(map(int, (version.split(".")))) >= (3, 4, 0):
        app = await model.deploy(
            "rabbitmq-k8s",
            channel="3.12/edge",
            trust=True,
        )
    else:
        app = await model.deploy(
            "rabbitmq-k8s",
            channel="3.12/edge",
            trust=True,
            series="jammy",
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
    try:
        if tuple(map(int, (version.split(".")))) >= (3, 4, 0):
            return await model.deploy("postgresql-k8s", channel="14/stable", trust=True)
        else:
            return await model.deploy(
                "postgresql-k8s", channel="14/stable", revision=300, trust=True
            )
    except JujuError as e:
        if 'cannot add application "postgresql-k8s": application already exists' in e.message:
            logger.info("Application 'postgresql-k8s' already exists")
            return model.applications["postgresql-k8s"]
        else:
            raise e


@pytest_asyncio.fixture(scope="module", name="openfga_server_app")
async def deploy_openfga_server_fixture(model: Model, postgresql_k8s: Application):
    """Deploy openfga k8s charm."""
    try:
        openfga_server_app = await model.deploy("openfga-k8s", channel="latest/stable")
        await model.integrate(openfga_server_app.name, postgresql_k8s.name)
        await model.wait_for_idle(
            apps=[openfga_server_app.name, postgresql_k8s.name], status="active"
        )
        return openfga_server_app
    except JujuError as e:
        if "application already exists" in str(e):
            logger.info(f"openfga-k8s is already deployed {e}")
            return model.applications["openfga-k8s"]
        else:
            raise e


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
