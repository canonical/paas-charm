# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import logging
import pathlib
import subprocess
from typing import cast

import jubilant
import pytest
import requests
import yaml
from pytest import Config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tests.integration.helpers import inject_charm_config, inject_venv
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


@pytest.fixture(scope="function", name="http")
def fixture_http_client():
    """Return the --test-flask-image test parameter."""
    retry_strategy = Retry(
        total=5,
        connect=5,
        read=5,
        other=5,
        backoff_factor=5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "POST", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    with requests.Session() as http:
        http.mount("http://", adapter)
        yield http


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


@pytest.fixture(scope="module", name="spring_boot_app_image")
def fixture_spring_boot_app_image(pytestconfig: Config):
    """Return the --paas-spring-boot-app-image test parameter."""
    image = pytestconfig.getoption("--paas-spring-boot-app-image")
    if not image:
        raise ValueError("the following arguments are required: --paas-spring-boot-app-image")
    return image


@pytest.fixture(scope="module", name="test_async_flask_image")
def fixture_test_async_flask_image(pytestconfig: pytest.Config):
    """Return the --test-async-flask-image test parameter."""
    test_flask_image = pytestconfig.getoption("--test-async-flask-image")
    if not test_flask_image:
        raise ValueError("the following arguments are required: --test-async-flask-image")
    return test_flask_image


def build_charm_file(
    pytestconfig: pytest.Config,
    framework: str,
    tmp_path_factory,
    charm_dict: dict = None,
    charm_location: pathlib.Path = None,
) -> str:
    """Get the existing charm file if exists, build a new one if not."""
    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"/{framework}-k8s" in f),
        None,
    )

    if not charm_file:
        if not charm_location:
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


@pytest.fixture(scope="module", name="flask_non_root_db_app")
def flask_non_root_db_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    test_db_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root flask charm with test-db-flask image."""
    framework = "flask"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=True,
        resources={
            "flask-app-image": test_db_flask_image,
        },
        charm_dict={"charm-user": "non-root"},
    )


@pytest.fixture(scope="module", name="flask_non_root_app")
def flask_non_root_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    test_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root flask charm with test-flask image and non-root charm user."""
    framework = "flask"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=False,
        resources={
            "flask-app-image": test_flask_image,
        },
        charm_dict={"charm-user": "non-root"},
    )


@pytest.fixture(scope="module", name="django_non_root_app")
def django_non_root_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    django_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root Django charm with django-app image."""
    framework = "django"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=True,
        config={"django-allowed-hosts": "*"},
        resources={
            "django-app-image": django_app_image,
        },
        charm_dict={"charm-user": "non-root"},
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


@pytest.fixture(scope="module", name="fastapi_non_root_app")
def fastapi_non_root_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    fastapi_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root FastAPI charm with fastapi-app image."""
    framework = "fastapi"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": fastapi_app_image,
        },
        config={"non-optional-string": "non-optional-value"},
        charm_dict={"charm-user": "non-root"},
    )


@pytest.fixture(scope="module", name="go_app")
def go_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
    framework = "go"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        use_postgres=True,
        tmp_path_factory=tmp_path_factory,
        config={"metrics-port": 8081},
    )


@pytest.fixture(scope="module", name="go_non_root_app")
def go_non_root_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    go_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root Go charm with go-app image."""
    framework = "go"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": go_app_image,
        },
        charm_dict={"charm-user": "non-root"},
    )


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

    use_existing = pytestconfig.getoption("--use-existing")
    if use_existing:
        return App(app_name)

    juju.deploy(
        "postgresql-k8s",
        channel="14/edge",
        base="ubuntu@22.04",
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


@pytest.fixture(scope="module", name="expressjs_non_root_app")
def expressjs_non_root_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    tmp_path_factory,
    expressjs_app_image: str,
):
    """Build and deploy the non-root Go charm with go-app image."""
    framework = "expressjs"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": expressjs_app_image,
        },
        charm_dict={"charm-user": "non-root"},
    )


@pytest.fixture(scope="module", name="spring_boot_app")
def spring_boot_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    tmp_path_factory,
    spring_boot_app_image: str,
):
    """Build and deploy the Go charm with go-app image."""
    app_name = "spring-boot-k8s"

    resources = {
        "app-image": spring_boot_app_image,
    }
    try:
        juju.deploy(
            "postgresql-k8s",
            channel="14/edge",
            base="ubuntu@22.04",
            trust=True,
            config={
                "profile": "testing",
                "plugin_hstore_enable": "true",
                "plugin_pg_trgm_enable": "true",
            },
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    charm_file = build_charm_file(
        pytestconfig,
        "spring-boot",
        tmp_path_factory,
        charm_location=PROJECT_ROOT / "examples/springboot/charm",
    )
    try:
        juju.deploy(
            charm=charm_file,
            app=app_name,
            resources=resources,
        )
    except jubilant.CLIError as err:
        if "application already exists" in err.stderr:
            juju.refresh(app_name, path=charm_file, resources=resources)
        else:
            raise err
    # Add required relations
    try:
        juju.integrate(app_name, "postgresql-k8s:database")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    juju.wait(
        lambda status: jubilant.all_active(status, app_name, "postgresql-k8s"),
        timeout=600,
    )

    return App(app_name)


@pytest.fixture(scope="module", name="spring_boot_mysql_app")
def spring_boot_mysql_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    spring_boot_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the Go charm with go-app image."""
    app_name = "spring-boot-k8s"

    resources = {
        "app-image": spring_boot_app_image,
    }
    file = PROJECT_ROOT / "examples/springboot/charm/charmcraft.yaml"

    charm_metadata = yaml.safe_load(file.read_text())
    updated_dict = {
        "requires": {
            **charm_metadata["requires"],
            "mysql": {
                "interface": "mysql_client",
                "optional": False,
                "limit": 1,
            },
            "postgresql": {
                "interface": "postgresql_client",
                "optional": True,
                "limit": 1,
            },
        }
    }

    charm_file = build_charm_file(
        pytestconfig,
        "spring-boot",
        tmp_path_factory,
        charm_dict=updated_dict,
        charm_location=PROJECT_ROOT / "examples/springboot/charm",
    )
    try:
        juju.deploy(
            charm=charm_file,
            app=app_name,
            resources=resources,
        )
    except jubilant.CLIError as err:
        if "application already exists" in err.stderr:
            juju.refresh(app_name, path=charm_file, resources=resources)
        else:
            raise err

    return App(app_name)


@pytest.fixture(scope="module", name="external_hostname")
def external_hostname_fixture() -> str:
    """Return the external hostname for ingress-related tests."""
    return "juju.test"


@pytest.fixture(scope="module", name="traefik_app_name")
def traefik_app_name_fixture() -> str:
    """Return the name of the traefik application deployed for tests."""
    return "traefik-k8s"


@pytest.fixture(scope="module", name="loki_app_name")
def loki_app_name_fixture() -> str:
    """Return the name of the prometheus application deployed for tests."""
    return "loki-k8s"


@pytest.fixture(scope="module", name="grafana_app_name")
def grafana_app_name_fixture() -> str:
    """Return the name of the grafana application deployed for tests."""
    return "grafana-k8s"


@pytest.fixture(scope="module", name="traefik_app")
def deploy_traefik_fixture(
    juju: jubilant.Juju,
    traefik_app_name: str,
    external_hostname: str,
):
    """Deploy traefik."""
    if not juju.status().apps.get(traefik_app_name):
        juju.deploy(
            "traefik-k8s",
            app=traefik_app_name,
            channel="edge",
            trust=True,
            config={
                "external_hostname": external_hostname,
                "routing_mode": "subdomain",
            },
        )
    juju.wait(
        lambda status: status.apps[traefik_app_name].is_active,
        error=jubilant.any_blocked,
    )
    return App(traefik_app_name)


@pytest.fixture(scope="module", name="redis_k8s_app")
def deploy_redis_k8s_jubilant_fixture(juju: jubilant.Juju):
    """Deploy Redis k8s charm using jubilant."""
    app_name = "redis-k8s"
    if not juju.status().apps.get(app_name):
        juju.deploy(app_name, channel="edge")
    juju.wait(lambda status: status.apps[app_name].is_active, error=jubilant.any_blocked)
    return App(app_name)


@pytest.fixture(scope="function", name="integrate_redis_k8s_flask")
def integrate_redis_k8s_flask_fixture(
    juju: jubilant.Juju,
    flask_app: App,
    redis_k8s_app: App,
):
    """Integrate redis_k8s with flask apps using jubilant."""
    try:
        juju.integrate(flask_app.name, redis_k8s_app.name)
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    juju.wait(lambda status: jubilant.all_active(status, flask_app.name, redis_k8s_app.name))

    yield

    # Teardown - remove relation
    juju.cli("remove-relation", flask_app.name, redis_k8s_app.name)
    juju.wait(lambda status: status.apps.get(flask_app.name) is not None, timeout=5 * 60)


@pytest.fixture(scope="session")
def juju(request: pytest.FixtureRequest) -> jubilant.Juju:
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        return juju

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        return juju

    keep_models = cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        return juju


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


@pytest.fixture(scope="module", name="django_async_app")
def django_async_app_fixture(juju: jubilant.Juju, pytestconfig: pytest.Config, tmp_path_factory):
    framework = "django-async"
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


def generate_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    framework: str,
    tmp_path_factory,
    image_name: str = "",
    use_postgres: bool = True,
    config: dict[str, jubilant.ConfigValue] | None = None,
    resources: dict[str, str] | None = None,
    charm_dict: dict | None = None,
):
    """Generates the charm, configures and deploys it and the relations it depends on."""
    app_name = f"{framework}-k8s"
    if image_name == "":
        image_name = f"{framework}-app-image"
    use_existing = pytestconfig.getoption("--use-existing")
    if use_existing:
        return App(app_name)
    if resources is None:
        resources = {
            "app-image": pytestconfig.getoption(f"--{image_name}"),
        }
    main_framework = framework
    # The async version of frameworks uses the same charm as the sync one
    if "-async" in main_framework:
        main_framework = main_framework.replace("-async", "")
    charm_file = build_charm_file(
        pytestconfig, main_framework, tmp_path_factory, charm_dict=charm_dict
    )
    try:
        juju.deploy(
            charm=charm_file,
            app=f"{framework}-k8s",
            resources=resources,
            config=config,
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    # Add required relations
    apps_to_wait_for = [app_name]
    if use_postgres:
        deploy_postgresql(juju)
        try:
            juju.integrate(app_name, "postgresql-k8s:database")
        except jubilant.CLIError as err:
            if "already exists" not in err.stderr:
                raise err
        apps_to_wait_for.append("postgresql-k8s")
    juju.wait(lambda status: jubilant.all_active(status, *apps_to_wait_for), timeout=10 * 60)
    yield App(app_name)


def deploy_postgresql(
    juju: jubilant.Juju,
):
    """Deploy and set up postgresql charm needed for the 12-factor charm."""

    if juju.status().apps.get("postgresql-k8s"):
        logger.info("postgresql-k8s already deployed")
        return

    juju.deploy(
        "postgresql-k8s",
        channel="14/edge",
        base="ubuntu@22.04",
        trust=True,
        config={
            "profile": "testing",
            "plugin_hstore_enable": "true",
            "plugin_pg_trgm_enable": "true",
        },
    )


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
        charm_dict={
            "config": {
                "options": {
                    "foo-str": {"type": "string"},
                    "foo-int": {"type": "int"},
                    "foo-bool": {"type": "boolean"},
                    "foo-dict": {"type": "string"},
                    "application-root": {"type": "string"},
                }
            }
        },
    )


@pytest.fixture(scope="module", name="flask_db_app")
def flask_db_app_fixture(
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
        resources={
            "flask-app-image": pytestconfig.getoption(f"--test-db-flask-image"),
        },
    )


@pytest.fixture(scope="module", name="flask_async_app")
def flask_async_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    tmp_path_factory,
):
    framework = "flask-async"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=False,
        resources={
            "flask-app-image": pytestconfig.getoption(f"--test-async-flask-image"),
        },
    )
