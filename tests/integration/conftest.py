# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import logging
import pathlib
import subprocess
from collections.abc import Generator
from typing import cast

import jubilant
import pytest
import pytest_asyncio
from juju.application import Application
from juju.errors import JujuError
from juju.juju import Juju
from juju.model import Model
from pytest import Config
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import (
    inject_charm_config,
    inject_venv,
)
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
logger = logging.getLogger(__name__)

NON_OPTIONAL_CONFIGS = {
    "config": {
        "options": {
            "non-optional-bool": {"type": "boolean", "optional": False},
            "non-optional-int": {"type": "int", "optional": False},
        }
    }
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


@pytest.fixture(scope="module", name="test_db_flask_image")
def fixture_test_db_flask_image(pytestconfig: Config):
    """Return the --test-flask-image test parameter."""
    test_flask_image = pytestconfig.getoption("--test-db-flask-image")
    if not test_flask_image:
        raise ValueError("the following arguments are required: --test-db-flask-image")
    return test_flask_image


@pytest.fixture(scope="module", name="expressjs_app_image")
def fixture_expressjs_app_image(pytestconfig: Config):
    """Return the --expressjs-app-image test parameter."""
    image = pytestconfig.getoption("--expressjs-app-image")
    if not image:
        raise ValueError("the following arguments are required: --expressjs-app-image")
    return image


@pytest.fixture(scope="module", name="flask_minimal_app_image")
def fixture_flask_minimal_app_image(pytestconfig: Config):
    """Return the --expressjs-app-image test parameter."""
    image = pytestconfig.getoption("--flask-minimal-app-image")
    if not image:
        raise ValueError("the following arguments are required: --flask-minimal-app-image")
    return image


def build_charm_file(
    pytestconfig: pytest.Config,
    framework: str,
    tmp_path_factory,
    charm_dict: dict = None,
) -> str:
    """Get the existing charm file if exists, build a new one if not."""
    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"/{framework}-k8s" in f),
        None,
    )

    if not charm_file:
        charm_location = PROJECT_ROOT / f"examples/{framework}/charm"
        try:
            subprocess.run(
                [
                    "charmcraft",
                    "pack",
                ],
                cwd=charm_location,
                check=True,
                capture_output=True,
                text=True,
            )
            app_name = f"{framework}-k8s"
            charm_path = pathlib.Path(charm_location)
            charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
            assert charms, f"{app_name} .charm file not found"
            assert (
                len(charms) == 1
            ), f"{app_name} has more than one .charm file, please remove any undesired .charm files"
            charm_file = str(charms[0])
        except subprocess.CalledProcessError as exc:
            raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    if charm_dict:
        charm_file = inject_charm_config(
            charm_file,
            charm_dict,
            tmp_path_factory.mktemp(framework),
        )
    return pathlib.Path(charm_file).absolute()


@pytest_asyncio.fixture(scope="module", name="flask_app")
async def flask_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    test_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the flask charm with test-flask image."""
    app_name = "flask-k8s"

    resources = {
        "flask-app-image": test_flask_image,
    }
    charm_file = build_charm_file(
        pytestconfig,
        "flask",
        tmp_path_factory,
    )
    app = await model.deploy(
        charm_file, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle(apps=[app_name], status="active", timeout=300, raise_on_blocked=True)
    return app


@pytest_asyncio.fixture(scope="module", name="loki_app")
async def deploy_loki_fixture(
    model: Model,
    loki_app_name: str,
):
    """Deploy loki."""
    app = await model.deploy(
        "loki-k8s", application_name=loki_app_name, channel="latest/stable", trust=True
    )
    await model.wait_for_idle(raise_on_blocked=True)

    return app


@pytest_asyncio.fixture(scope="module", name="flask_non_root_db_app")
async def flask_non_root_db_app_fixture(
    pytestconfig: pytest.Config,
    postgresql_k8s,
    model: Model,
    test_db_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root flask charm with test-db-flask image."""
    app_name = "flask-k8s"

    resources = {
        "flask-app-image": test_db_flask_image,
    }
    charm_file = build_charm_file(
        pytestconfig, "flask", tmp_path_factory, {"charm-user": "non-root"}
    )
    app = await model.deploy(
        charm_file, resources=resources, application_name=app_name, series="jammy"
    )
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name, app_name], status="active", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="flask_non_root_app")
async def flask_non_root_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    test_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root flask charm with test-flask image and non-root charm user."""
    app_name = "flask-k8s"

    resources = {
        "flask-app-image": test_flask_image,
    }
    charm_file = build_charm_file(
        pytestconfig, "flask", tmp_path_factory, {"charm-user": "non-root"}
    )
    app = await model.deploy(
        charm_file, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle(apps=[app_name], status="active", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="flask_blocked_app")
async def flask_blocked_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    test_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the flask charm with test-flask image."""
    app_name = "flask-k8s"

    resources = {
        "flask-app-image": test_flask_image,
    }
    charm_file = build_charm_file(pytestconfig, "flask", tmp_path_factory, NON_OPTIONAL_CONFIGS)
    app = await model.deploy(
        charm_file, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle(apps=[app_name], status="blocked", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="django_app")
async def django_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    django_app_image: str,
    postgresql_k8s: Application,
    tmp_path_factory,
):
    """Build and deploy the Django charm with django-app image."""
    app_name = "django-k8s"

    resources = {
        "django-app-image": django_app_image,
    }
    charm_file = build_charm_file(pytestconfig, "django", tmp_path_factory)

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
    model: Model,
    django_app_image: str,
    postgresql_k8s: Application,
    tmp_path_factory,
):
    """Build and deploy the Django charm with django-app image."""
    app_name = "django-k8s"

    resources = {
        "django-app-image": django_app_image,
    }
    charm_file = build_charm_file(pytestconfig, "django", tmp_path_factory, NON_OPTIONAL_CONFIGS)

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


@pytest_asyncio.fixture(scope="module", name="django_non_root_app")
async def django_non_root_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    django_app_image: str,
    postgresql_k8s: Application,
    tmp_path_factory,
):
    """Build and deploy the non-root Django charm with django-app image."""
    app_name = "django-k8s"

    resources = {
        "django-app-image": django_app_image,
    }
    charm_file = build_charm_file(
        pytestconfig, "django", tmp_path_factory, {"charm-user": "non-root"}
    )

    app = await model.deploy(
        charm_file,
        resources=resources,
        config={"django-allowed-hosts": "*"},
        application_name=app_name,
        series="jammy",
    )
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name, app_name], status="active", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="fastapi_app")
async def fastapi_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    fastapi_app_image: str,
    postgresql_k8s: Application,
    tmp_path_factory,
):
    """Build and deploy the FastAPI charm with fastapi-app image."""
    app_name = "fastapi-k8s"

    resources = {
        "app-image": fastapi_app_image,
    }
    charm_file = build_charm_file(pytestconfig, "fastapi", tmp_path_factory)
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
    model: Model,
    fastapi_app_image: str,
    postgresql_k8s: Application,
    tmp_path_factory,
):
    """Build and deploy the FastAPI charm with fastapi-app image."""
    app_name = "fastapi-k8s"

    resources = {"app-image": fastapi_app_image}
    charm_file = build_charm_file(pytestconfig, "fastapi", tmp_path_factory, NON_OPTIONAL_CONFIGS)
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name], status="active", timeout=300)
    await model.wait_for_idle(apps=[app_name], status="blocked", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="fastapi_non_root_app")
async def fastapi_non_root_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    fastapi_app_image: str,
    postgresql_k8s: Application,
    tmp_path_factory,
):
    """Build and deploy the non-root FastAPI charm with fastapi-app image."""
    app_name = "fastapi-k8s"

    resources = {"app-image": fastapi_app_image}
    charm_file = build_charm_file(
        pytestconfig, "fastapi", tmp_path_factory, {"charm-user": "non-root"}
    )
    app = await model.deploy(
        charm_file,
        resources=resources,
        application_name=app_name,
        config={"non-optional-string": "non-optional-value"},
    )
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name, app_name], status="active", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="go_app")
async def go_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    go_app_image: str,
    postgresql_k8s,
    tmp_path_factory,
):
    """Build and deploy the Go charm with go-app image."""
    app_name = "go-k8s"

    resources = {
        "app-image": go_app_image,
    }
    charm_file = build_charm_file(pytestconfig, "go", tmp_path_factory)
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[app_name, postgresql_k8s.name], status="active", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="go_blocked_app")
async def go_blocked_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    go_app_image: str,
    postgresql_k8s,
    tmp_path_factory,
):
    """Build and deploy the Go charm with go-app image."""
    app_name = "go-k8s"

    resources = {
        "app-image": go_app_image,
    }
    charm_file = build_charm_file(pytestconfig, "go", tmp_path_factory, NON_OPTIONAL_CONFIGS)
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name], status="active", timeout=300)
    await model.wait_for_idle(apps=[app_name], status="blocked", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="go_non_root_app")
async def go_non_root_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    go_app_image: str,
    postgresql_k8s,
    tmp_path_factory,
):
    """Build and deploy the non-root Go charm with go-app image."""
    app_name = "go-k8s"

    resources = {
        "app-image": go_app_image,
    }
    charm_file = build_charm_file(pytestconfig, "go", tmp_path_factory, {"charm-user": "non-root"})
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name, app_name], status="active", timeout=300)
    return app


@pytest.fixture(scope="module", name="expressjs_app")
def expressjs_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    tmp_path_factory,
):
    """ExpressJS charm used for integration testing.
    Builds the charm and deploys it and the relations it depends on.
    """
    app_name = "expressjs-k8s"

    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return App(app_name)

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

    resources = {
        "app-image": pytestconfig.getoption("--expressjs-app-image"),
    }
    charm_file = build_charm_file(pytestconfig, "expressjs", tmp_path_factory)
    juju.deploy(
        charm=charm_file,
        resources=resources,
    )

    # Add required relations
    juju.integrate(app_name, "postgresql-k8s:database")
    juju.wait(
        lambda status: jubilant.all_active(status, app_name, "postgresql-k8s"),
        timeout=300,
    )

    return App(app_name)


@pytest_asyncio.fixture(scope="module", name="expressjs_blocked_app")
async def expressjs_blocked_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    expressjs_app_image: str,
    postgresql_k8s,
    tmp_path_factory,
):
    """Build and deploy the ExpressJS charm with expressjs-app image."""
    app_name = "expressjs-k8s"

    resources = {
        "app-image": expressjs_app_image,
    }
    charm_file = build_charm_file(
        pytestconfig, "expressjs", tmp_path_factory, NON_OPTIONAL_CONFIGS
    )
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name], status="active", timeout=300)
    await model.wait_for_idle(apps=[app_name], status="blocked", timeout=300)
    return app


@pytest_asyncio.fixture(scope="module", name="expressjs_non_root_app")
async def expressjs_non_root_app_fixture(
    pytestconfig: pytest.Config,
    model: Model,
    expressjs_app_image: str,
    postgresql_k8s,
    tmp_path_factory,
):
    """Build and deploy the non-root Go charm with go-app image."""
    app_name = "expressjs-k8s"

    resources = {
        "app-image": expressjs_app_image,
    }
    charm_file = build_charm_file(
        pytestconfig, "expressjs", tmp_path_factory, {"charm-user": "non-root"}
    )
    app = await model.deploy(charm_file, resources=resources, application_name=app_name)
    await model.integrate(app_name, postgresql_k8s.name)
    await model.wait_for_idle(apps=[postgresql_k8s.name, app_name], status="active", timeout=300)
    return app


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
        channel="1/stable",
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


@pytest.fixture(scope="session")
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
