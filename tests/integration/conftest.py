# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import logging
import pathlib
import subprocess
from collections.abc import Generator
from typing import cast

import jubilant
import pytest
from ops import JujuVersion
from pytest import Config, FixtureRequest

from tests.integration.helpers import inject_charm_config, inject_venv
from tests.integration.types import App

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


@pytest.fixture(scope="module", name="test_async_flask_image")
def fixture_test_async_flask_image(pytestconfig: Config):
    """Return the --test-async-flask-image test parameter."""
    test_flask_image = pytestconfig.getoption("--test-async-flask-image")
    if not test_flask_image:
        raise ValueError("the following arguments are required: --test-async-flask-image")
    return test_flask_image


@pytest.fixture(scope="module", name="test_db_flask_image")
def fixture_test_db_flask_image(pytestconfig: Config):
    """Return the --test-flask-image test parameter."""
    test_flask_image = pytestconfig.getoption("--test-db-flask-image")
    if not test_flask_image:
        raise ValueError("the following arguments are required: --test-db-flask-image")
    return test_flask_image


@pytest.fixture(scope="module", name="django_app_image")
def fixture_django_app_image(pytestconfig: Config):
    """Return the --django-app-image test parameter."""
    image = pytestconfig.getoption("--django-app-image")
    if not image:
        raise ValueError("the following arguments are required: --django-app-image")
    return image

@pytest.fixture(scope="module", name="django_async_app_image")
def fixture_django_async_app_image(pytestconfig: Config):
    """Return the --django-async-app-image test parameter."""
    image = pytestconfig.getoption("--django-async-app-image")
    if not image:
        raise ValueError("the following arguments are required: --django-async-app-image")
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
    config_options: dict = {},
) -> str:
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
            ), f"{app_name} has more than one .charm file, unsure which to use"
            charm_file = str(charms[0])
        except subprocess.CalledProcessError as exc:
            raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    if config_options:
        charm_file = inject_charm_config(
            charm_file,
            config_options,
            charm_path,
        )
    return pathlib.Path(charm_file).absolute()



@pytest.fixture(scope="function", name="flask_app")
def flask_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "flask"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            image_name=f"test-{framework}-image",
            use_postgres=False,
        )
    )

@pytest.fixture(scope="function", name="flask_db_app")
def flask_db_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "flask"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            image_name=f"test-db-{framework}-image",
        )
    )

@pytest.fixture(scope="function", name="flask_async_app")
def flask_async_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "flask"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            image_name=f"test-async-{framework}-image",
            app_name=f"{framework}-async-k8s",
            use_postgres=False,
        )
    )


@pytest.fixture(scope="function", name="flask_blocked_app")
def flask_blocked_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "flask"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            image_name=f"test-{framework}-image",
            use_postgres=False,
            config_options=NON_OPTIONAL_CONFIGS,
            expected_status="blocked",
        )
    )
@pytest.fixture(scope="function", name="flask_minimal_app")
def flask_minimal_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "flask-minimal"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            image_name=f"{framework}-app-image",
            use_postgres=False,
        )
    )



@pytest.fixture(scope="module", name="django_app")
def django_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "django"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
        )
    )

@pytest.fixture(scope="module", name="django_async_app")
def django_async_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "django"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            image_name="django-async-app-image",
            app_name="django-async-k8s",
        )
    )

@pytest.fixture(scope="module", name="django_blocked_app")
def django_blocked_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "django"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            config_options=NON_OPTIONAL_CONFIGS,
            expected_status="blocked",
        )
    )


@pytest.fixture(scope="function", name="fastapi_app")
@pytest.mark.skip_juju_version("3.4")
def fastapi_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "fastapi"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
        )
    )


@pytest.fixture(scope="module", name="fastapi_blocked_app")
def fastapi_blocked_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "fastapi"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            config_options=NON_OPTIONAL_CONFIGS,
            expected_status="blocked",
        )
    )



@pytest.fixture(scope="module", name="go_app")
def go_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "go"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
        )
    )


@pytest.fixture(scope="module", name="go_blocked_app")
def go_blocked_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "go"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            config_options=NON_OPTIONAL_CONFIGS,
            expected_status="blocked",
        )
    )


@pytest.fixture(scope="function", name="expressjs_app")
@pytest.mark.skip_juju_version("3.4")
def expressjs_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "expressjs"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
        )
    )

@pytest.fixture(scope="function", name="expressjs_blocked_app")
@pytest.mark.skip_juju_version("3.4")
def expressjs_blocked_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config):
    framework = "expressjs"
    yield next(
        generate_app_fixture(
            juju=juju,
            pytestconfig=pytestconfig,
            framework=framework,
            config_options=NON_OPTIONAL_CONFIGS,
            expected_status="blocked",
        )
    )


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
        config={"profile": "testing"},
    )
    juju.wait(
        lambda status: status.apps["postgresql-k8s"].is_active,
        timeout=20 * 60,
    )
    juju.config(
        "postgresql-k8s",
        {
            "plugin_hstore_enable": "true",
            "plugin_pg_trgm_enable": "true",
        },
    )
    juju.wait(lambda status: status.apps["postgresql-k8s"].is_active)

def generate_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    framework: str,
    image_name: str = "",
    app_name: str = "",
    use_postgres: bool = True,
    config_options: dict = {},
    expected_status: str = "active",
):
    """Discourse charm used for integration testing.
    Builds the charm and deploys it and the relations it depends on.
    """
    if app_name == "":
        app_name = f"{framework}-k8s"
    if image_name == "":
        image_name = f"{framework}-app-image"
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield App(app_name)
        juju.remove_application(app_name, destroy_storage=True, force=True)
        juju.wait(lambda status: status.apps.get(app_name) is None)
        return
    config = {}
    resources = {
        "app-image": pytestconfig.getoption(f"--{image_name}"),
    }
    # covers both flask and flask-minimal
    if framework.startswith("flask"):
        resources = {
            "flask-app-image": pytestconfig.getoption(f"--{image_name}"),
        }
    if framework.startswith("django"):
        resources = {
            "django-app-image": pytestconfig.getoption(f"--{image_name}"),
        }
        config = {"django-allowed-hosts": "*"}
    if framework == "fastapi":
        config = {"non-optional-string": "string"}
    # charm_file = await build_charm_file_with_config_options(
    #     pytestconfig, ops_test, tmp_path_factory, "django", NON_OPTIONAL_CONFIGS
    # )
    charm_file = build_charm_file(pytestconfig, framework, config_options)
    juju.deploy(
        charm=charm_file,
        app=app_name,
        resources=resources,
        config=config,
    )

    # Add required relations
    if use_postgres:
        deploy_postgresql(juju)
        juju.integrate(app_name, "postgresql-k8s:database")
        juju.wait(lambda status: status.apps["postgresql-k8s"].is_active, timeout=30 * 60)
    juju.wait(lambda status: status.apps[app_name].app_status.current == expected_status, timeout=10 * 60)

    yield App(app_name)
    # cleanup
    # remove the charm
    juju.remove_application(app_name, destroy_storage=True, force=True)
    juju.wait(lambda status: status.apps.get(app_name) is None)




@pytest.fixture(scope="module", name="juju_lxd")
def juju_lxd_fixture():
    """Return a ops_test fixture for lxd, creating the lxd controller if it does not exist."""
    if "lxd" not in juju.cli("controllers"):
        logger.info("bootstrapping lxd")
        _, _, _ = juju.cli("bootstrap", "localhost", "lxd")

    juju = jubilant.Juju(model="lxd:default") 
    # The instance is not stored in _instance as that is done for the ops_test fixture
    yield juju
    juju.destroy_model("lxd:default", destroy_storage=True, force=True)



@pytest.mark.skip_juju_version("3.4")
@pytest.fixture(scope="module", name="rabbitmq_server_app")  # autouse=True)
def deploy_rabbitmq_server_fixture(
    juju_lxd: jubilant.Juju,
) -> App:
    """Deploy rabbitmq-server machine app."""
    app = App("rabbitmq-server")
    juju_lxd.deploy(
        app.name,
        channel="latest/edge",
        base="ubuntu@22.04",
    )

    juju_lxd.wait(
        lambda status: status.apps[app.name].is_active,
        error=jubilant.any_blocked,)
    juju_lxd.offer(app.name,'amqp')
    yield app


@pytest.mark.skip_juju_version("3.4")
@pytest.fixture(scope="module", name="rabbitmq_k8s_app")  # autouse=True)
def deploy_rabbitmq_k8s_fixture(
    juju: jubilant.Juju,
) -> App:
    """Deploy rabbitmq-k8s app."""

    app = App("rabbitmq-k8s")
    juju.deploy(
        app.name,
        channel="3.12/edge",
        trust=True,
        base="ubuntu@22.04",
    )

    juju.wait(
        lambda status: status.apps[app.name].is_active,
        error=jubilant.any_blocked,
    )
    yield app


@pytest.fixture(scope="module", name="get_unit_ips")
def fixture_get_unit_ips(juju: jubilant.Juju):
    """Return a function to retrieve unit ip addresses of a certain application."""

    def get_unit_ips(application_name: str):
        """Retrieve unit ip addresses of a certain application.

        Returns:
            A list containing unit ip addresses.
        """
        status = juju.status()
        unit_ips = []
        if application_name not in status.apps:
            return unit_ips
        for unit in  status.apps[application_name].units:
            unit_ips.append(status.apps[application_name].units[unit].address)
        return tuple(unit_ips)

    return get_unit_ips


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
    """Return the name of the loki application deployed for tests."""
    return "loki-k8s"


@pytest.fixture(scope="module", name="grafana_app_name")
def grafana_app_name_fixture() -> str:
    """Return the name of the grafana application deployed for tests."""
    return "grafana-k8s"



@pytest.fixture(scope="module", name="redis_k8s_app")
def deploy_redisk8s_fixture(juju: jubilant.Juju) -> App:
    """Deploy Redis k8s charm."""
    app = App("redis-k8s")
    juju.deploy(
        app.name,
        channel="edge",
    )
    juju.wait(
        lambda status: status.apps[app.name].is_active,
    )
    return app


@pytest.fixture(scope="function", name="integrate_redis_k8s_flask")
def integrate_redis_k8s_flask_fixture(
    juju: jubilant.Juju, flask_app: App, redis_k8s_app: App
):
    """Integrate redis_k8s with flask apps."""
    juju.integrate(flask_app.name, redis_k8s_app.name)
    juju.wait(
        lambda status: jubilant.all_active(status, [flask_app.name, redis_k8s_app.name]))
    yield
    juju.remove_relation(flask_app.name, f"{redis_k8s_app.name}:redis")
    juju.wait(
        lambda status: jubilant.all_active(status))


# TODO: UPdate this to use it in all frameworks
@pytest.fixture
def update_config(
    juju: jubilant.Juju,
    request: FixtureRequest):
    """Update the django application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    app_name, new_config = request.param
    app = request.getfixturevalue(app_name)
    app_config_dict = juju.config(app.name)
    orig_config = {k: v for k, v in app_config_dict.items()}
    request_config = {k: str(v) for k, v in new_config.items()}
    juju.config(app.name, request_config)
    juju.wait(
        lambda status: jubilant.all_active(status, [app.name]),
    )

    yield request_config

    juju.config(
        app.name,
        {k: v for k, v in orig_config.items() if k in request_config and v is not None}
    )
    juju.config(
        app.name,
    {k: None for k in request_config if orig_config[k] is None})
    juju.wait(
        lambda status: jubilant.all_active(status, [app.name]),
    )

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


@pytest.fixture(autouse=True)
def skip_by_juju_version(request, juju: jubilant.Juju):
    """Skip the test if juju version is lower then the `skip_juju_version` marker value."""
    if request.node.get_closest_marker("skip_juju_version"):
        status = juju.status()
        current_version = JujuVersion(status.model.version)
        min_version = JujuVersion(request.node.get_closest_marker("skip_juju_version").args[0])
        if current_version < min_version:
            pytest.skip("Juju version is too old")


def pytest_configure(config):
    """Add new marker."""
    config.addinivalue_line(
        "markers",
        "skip_juju_version(version): skip test if Juju version is lower than version",
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
            channel="1.0/stable",
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


@pytest.fixture(scope="function", name="cos_apps")
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
            channel="1.0/stable",
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
    yield {
        "loki_app": loki_app,
        "prometheus_app": prometheus_app,
        "grafana_app": App(grafana_app_name),
    }