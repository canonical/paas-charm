# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import contextlib
import ipaddress
import logging
import pathlib
import shutil
import subprocess
from typing import cast

import jubilant
import pytest
import requests
import urllib3.util.connection
import yaml
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_fixed
from urllib3.util.retry import Retry

from tests.integration.helpers import inject_charm_config, inject_venv
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
logger = logging.getLogger(__name__)

INGRESS_HOSTNAME = "gateway.internal"

NON_OPTIONAL_CONFIGS = {
    "config": {
        "options": {
            "non-optional-bool": {"type": "boolean", "optional": False},
            "non-optional-int": {"type": "int", "optional": False},
        }
    }
}


@pytest.fixture(scope="function", name="session_with_retry")
def fixture_session_with_retry():
    """Return the --test-flask-image test parameter."""
    retry_strategy = Retry(
        total=5,
        connect=5,
        read=5,
        other=5,
        backoff_factor=5,
        status_forcelist=[404, 429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "POST", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    with requests.Session() as session_with_retry:
        session_with_retry.mount("http://", adapter)
        yield session_with_retry


@pytest.fixture(scope="session", name="rock_images")
def fixture_rock_images() -> dict[str, str]:
    """Return dict of built rock images from opcli artifacts.build.yaml.

    Maps rock names (e.g., "test-flask", "django-app") to OCI image URLs or
    local .rock file paths. Requires artifacts.build.yaml to exist; run
    'opcli artifacts build' to generate it before running integration tests.
    """
    artifacts_build = PROJECT_ROOT / "artifacts.build.yaml"
    if not artifacts_build.exists():
        pytest.fail(
            f"{artifacts_build} not found. Run 'opcli artifacts build' to generate "
            "build artifacts before running integration tests."
        )
    data = yaml.safe_load(artifacts_build.read_text())
    # artifacts.build.yaml uses a list of GeneratedRock objects:
    # rocks:
    #   - name: test-flask
    #     builds:
    #       - arch: amd64
    #         image: ghcr.io/...   (registry build)
    #         # or file: ./path/to.rock  (local build)
    result = {}
    for rock in data.get("rocks", []):
        name = rock["name"]
        for build in rock.get("builds", []):
            ref = build.get("image") or build.get("file") or ""
            if ref:
                result[name] = ref
                break
    return result


@pytest.fixture(scope="session", name="charm_paths")
def fixture_charm_paths() -> dict[str, pathlib.Path]:
    """Return dict of pre-built charm paths from opcli artifacts.build.yaml.

    Maps charm names (e.g., "flask-k8s", "django-k8s") to local .charm file
    paths. Requires artifacts.build.yaml to exist; run 'opcli artifacts build'
    to generate it before running integration tests.
    """
    artifacts_build = PROJECT_ROOT / "artifacts.build.yaml"
    if not artifacts_build.exists():
        pytest.fail(
            f"{artifacts_build} not found. Run 'opcli artifacts build' to generate "
            "build artifacts before running integration tests."
        )
    data = yaml.safe_load(artifacts_build.read_text())
    # artifacts.build.yaml uses a list of GeneratedCharm objects:
    # charms:
    #   - name: flask-k8s
    #     builds:
    #       - arch: amd64
    #         path: ./flask-k8s_ubuntu@26.04-amd64.charm
    result = {}
    for charm in data.get("charms", []):
        name = charm["name"]
        for build in charm.get("builds", []):
            path = build.get("path")
            if path:
                # Resolve relative to PROJECT_ROOT so shutil.copy2 can
                # find the file regardless of the pytest working directory.
                result[name] = (PROJECT_ROOT / path).resolve()
                break
    return result


@pytest.fixture(scope="module", name="test_flask_image")
def fixture_test_flask_image(rock_images: dict[str, str]):
    """Return the test-flask rock image URL."""
    image = rock_images.get("test-flask", "")
    if not image:
        raise ValueError("test-flask rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="test_async_flask_image")
def fixture_test_async_flask_image(rock_images: dict[str, str]):
    """Return the test-async-flask rock image URL."""
    image = rock_images.get("test-async-flask", "")
    if not image:
        raise ValueError("test-async-flask rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="test_db_flask_image")
def fixture_test_db_flask_image(rock_images: dict[str, str]):
    """Return the test-db-flask rock image URL."""
    image = rock_images.get("test-db-flask", "")
    if not image:
        raise ValueError("test-db-flask rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="django_app_image")
def fixture_django_app_image(rock_images: dict[str, str]):
    """Return the django-app rock image URL."""
    image = rock_images.get("django-app", "")
    if not image:
        raise ValueError("django-app rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="django_async_app_image")
def fixture_django_async_app_image(rock_images: dict[str, str]):
    """Return the django-async-app rock image URL."""
    image = rock_images.get("django-async-app", "")
    if not image:
        raise ValueError("django-async-app rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="fastapi_app_image")
def fixture_fastapi_app_image(rock_images: dict[str, str]):
    """Return the fastapi-app rock image URL."""
    image = rock_images.get("fastapi-app", "")
    if not image:
        raise ValueError("fastapi-app rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="go_app_image")
def fixture_go_app_image(rock_images: dict[str, str]):
    """Return the go-app rock image URL."""
    image = rock_images.get("go-app", "")
    if not image:
        raise ValueError("go-app rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="expressjs_app_image")
def fixture_expressjs_app_image(rock_images: dict[str, str]):
    """Return the expressjs-app rock image URL."""
    image = rock_images.get("expressjs-app", "")
    if not image:
        raise ValueError("expressjs-app rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="flask_minimal_app_image")
def fixture_flask_minimal_app_image(rock_images: dict[str, str]):
    """Return the flask-minimal-app rock image URL."""
    image = rock_images.get("flask-minimal-app", "")
    if not image:
        raise ValueError("flask-minimal-app rock image not found in artifacts.build.yaml")
    return image


@pytest.fixture(scope="module", name="spring_boot_app_image")
def fixture_spring_boot_app_image(rock_images: dict[str, str]):
    """Return the paas-spring-boot-app rock image URL."""
    image = rock_images.get("paas-spring-boot-app", "")
    if not image:
        raise ValueError("paas-spring-boot-app rock image not found in artifacts.build.yaml")
    return image


def build_charm_file(
    charm_paths: dict[str, pathlib.Path],
    framework: str,
    tmp_path_factory,
    charm_dict: dict = None,
    charm_location: pathlib.Path = None,
) -> pathlib.Path:
    """Build or retrieve charm file, apply injections, and return path.

    Uses pre-built charm from charm_paths if available, otherwise builds locally.
    Always copies to tmp before injecting venv/config to avoid mutating shared artifacts.
    """
    # Try to find pre-built charm in charm_paths
    charm_key = f"{framework}-k8s"
    if charm_key in charm_paths:
        built_charm = charm_paths[charm_key]
        # Copy to temp dir so inject_venv doesn't mutate shared artifact
        tmp_dir = tmp_path_factory.mktemp(f"{framework}-charm")
        charm_file = tmp_dir / built_charm.name
        shutil.copy2(built_charm, charm_file)
    else:
        # Build locally
        if not charm_location:
            charm_location = PROJECT_ROOT / f"examples/{framework}/charm"
        try:
            subprocess.run(
                ["charmcraft", "pack"],
                cwd=charm_location,
                check=True,
                capture_output=True,
                text=True,
            )
            charms = list(charm_location.glob(f"{charm_key}_*.charm"))
            assert charms, f"{charm_key} .charm file not found"
            assert (
                len(charms) == 1
            ), f"{charm_key} has more than one .charm file, please remove any undesired .charm files"
            # Copy to temp dir
            tmp_dir = tmp_path_factory.mktemp(f"{framework}-charm")
            charm_file = tmp_dir / charms[0].name
            shutil.copy2(charms[0], charm_file)
        except subprocess.CalledProcessError as exc:
            raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    # Apply injections to the temp copy
    inject_venv(str(charm_file), PROJECT_ROOT / "src" / "paas_charm")
    if charm_dict:
        charm_file = pathlib.Path(
            inject_charm_config(
                str(charm_file),
                charm_dict,
                tmp_path_factory.mktemp(f"{framework}-config"),
            )
        )

    return charm_file.absolute()


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
    charm_paths: dict[str, pathlib.Path],
    test_db_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root flask charm with test-db-flask image."""
    framework = "flask"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=True,
        resources={
            "app-image": test_db_flask_image,
        },
        charm_dict={"charm-user": "non-root"},
    )


@pytest.fixture(scope="module", name="flask_non_root_app")
def flask_non_root_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    test_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root flask charm with test-flask image and non-root charm user."""
    framework = "flask"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=False,
        resources={
            "app-image": test_flask_image,
        },
        charm_dict={"charm-user": "non-root"},
    )


@pytest.fixture(scope="module", name="django_non_root_app")
def django_non_root_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    django_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root Django charm with django-app image."""
    framework = "django"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=True,
        config={"django-allowed-hosts": "*"},
        resources={
            "app-image": django_app_image,
        },
        charm_dict={"charm-user": "non-root"},
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


@pytest.fixture(scope="module", name="fastapi_non_root_app")
def fastapi_non_root_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    fastapi_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root FastAPI charm with fastapi-app image."""
    framework = "fastapi"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": fastapi_app_image,
        },
        config={"non-optional-string": "non-optional-value"},
        charm_dict={"charm-user": "non-root"},
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
        use_postgres=True,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": go_app_image,
        },
        config={"metrics-port": 8081},
    )


@pytest.fixture(scope="module", name="go_non_root_app")
def go_non_root_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    go_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the non-root Go charm with go-app image."""
    framework = "go"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
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
    charm_paths: dict[str, pathlib.Path],
    expressjs_app_image: str,
    tmp_path_factory,
):
    """ExpressJS charm used for integration testing.
    Builds the charm and deploys it and the relations it depends on.
    """
    app_name = "expressjs-k8s"

    deploy_postgresql(juju)

    resources = {
        "app-image": expressjs_app_image,
    }
    charm_file = build_charm_file(charm_paths, "expressjs", tmp_path_factory)
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
    charm_paths: dict[str, pathlib.Path],
    tmp_path_factory,
    expressjs_app_image: str,
):
    """Build and deploy the non-root ExpressJS charm with expressjs-app image."""
    framework = "expressjs"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=True,
        resources={
            "app-image": expressjs_app_image,
        },
        charm_dict={"charm-user": "non-root"},
    )


@pytest.fixture(scope="module", name="spring_boot_app")
def spring_boot_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    tmp_path_factory,
    spring_boot_app_image: str,
):
    """Build and deploy the Spring Boot charm with spring-boot-app image."""
    app_name = "spring-boot-k8s"

    resources = {
        "app-image": spring_boot_app_image,
    }
    deploy_postgresql(juju)

    charm_file = build_charm_file(
        charm_paths,
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
    charm_paths: dict[str, pathlib.Path],
    spring_boot_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the Spring Boot charm with MySQL integration."""
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
        charm_paths,
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


@pytest.fixture(scope="module", name="ingress_provider")
def ingress_provider_fixture(
    juju: jubilant.Juju,
):
    """Deploy gateway-api-integrator and ingress-configurator for ingress-related tests."""
    juju.deploy(
        charm="gateway-api-integrator",
        app="gateway",
        channel="1/edge",
        trust=True,
        config={"gateway-class": "ck-gateway"},
    )
    juju.deploy(
        charm="ingress-configurator",
        app="configurator",
        channel="latest/edge",
        trust=True,
        config={"hostname": INGRESS_HOSTNAME},
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
    """Return the load-balancer IP of the gateway application."""
    @retry(stop=stop_after_attempt(12), wait=wait_fixed(5))
    def _gateway_lb_ip() -> str:
        gateway_app, _ = ingress_provider
        message = juju.status().apps[gateway_app].app_status.message or ""
        for token in message.split():
            try:
                return str(ipaddress.ip_address(token.strip("[](),;")))
            except ValueError:
                continue
        raise ValueError(f"Could not parse gateway load-balancer IP from status message: {message!r}")

    return _gateway_lb_ip()


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


@pytest.fixture(scope="module", name="loki_app_name")
def loki_app_name_fixture() -> str:
    """Return the name of the prometheus application deployed for tests."""
    return "loki-k8s"


@pytest.fixture(scope="module", name="grafana_app_name")
def grafana_app_name_fixture() -> str:
    """Return the name of the grafana application deployed for tests."""
    return "grafana-k8s"


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

    # Ensure the active/default Juju controller is the Kubernetes one (CI: concierge-k8s)
    # so temporary models and k8s charm deploys land on a Kubernetes cloud.
    controller = request.config.getoption("--controller")
    jubilant.Juju().cli("switch", controller, include_model=False)

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        return juju

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        return juju

    keep_models = cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models, controller=controller) as juju:
        juju.wait_timeout = 10 * 60
        return juju


@pytest.fixture(scope="module", name="django_app")
def django_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    django_app_image: str,
    tmp_path_factory,
):
    framework = "django"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        config={"django-allowed-hosts": "*"},
        resources={
            "app-image": django_app_image,
        },
    )


@pytest.fixture(scope="module", name="django_async_app")
def django_async_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    django_async_app_image: str,
    tmp_path_factory,
):
    framework = "django-async"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        config={"django-allowed-hosts": "*"},
        resources={
            "app-image": django_async_app_image,
        },
    )


def generate_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
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
    if use_postgres:
        deploy_postgresql(juju)
    if resources is None:
        resources = {}
    main_framework = framework
    # The async version of frameworks uses the same charm as the sync one
    if "-async" in main_framework:
        main_framework = main_framework.replace("-async", "")
    charm_file = build_charm_file(
        charm_paths, main_framework, tmp_path_factory, charm_dict=charm_dict
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
    charm_paths: dict[str, pathlib.Path],
    test_flask_image: str,
    tmp_path_factory,
):
    framework = "flask"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=False,
        resources={
            "app-image": test_flask_image,
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
    charm_paths: dict[str, pathlib.Path],
    test_db_flask_image: str,
    tmp_path_factory,
):
    framework = "flask"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        resources={
            "app-image": test_db_flask_image,
        },
    )


@pytest.fixture(scope="module", name="flask_async_app")
def flask_async_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    test_async_flask_image: str,
    tmp_path_factory,
):
    framework = "flask-async"
    yield from generate_app_fixture(
        juju=juju,
        charm_paths=charm_paths,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=False,
        resources={
            "app-image": test_async_flask_image,
        },
    )


# Jubilant-based blocked app fixtures for test_config.py
@pytest.fixture(scope="module", name="flask_blocked_app")
def flask_blocked_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    test_flask_image: str,
    tmp_path_factory,
):
    """Build and deploy the flask charm with non-optional configs using jubilant."""
    app_name = "flask-k8s"

    resources = {"app-image": test_flask_image}
    charm_file = build_charm_file(
        charm_paths, "flask", tmp_path_factory, charm_dict=NON_OPTIONAL_CONFIGS
    )

    try:
        juju.deploy(charm=str(charm_file), app=app_name, resources=resources)
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: status.apps[app_name].is_blocked, timeout=5 * 60)
    return App(app_name)


@pytest.fixture(scope="module", name="django_blocked_app")
def django_blocked_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    django_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the Django charm with non-optional configs using jubilant."""
    app_name = "django-k8s"

    resources = {"app-image": django_app_image}
    charm_file = build_charm_file(
        charm_paths, "django", tmp_path_factory, charm_dict=NON_OPTIONAL_CONFIGS
    )

    try:
        juju.deploy(
            charm=str(charm_file),
            app=app_name,
            resources=resources,
            config={"django-allowed-hosts": "*"},
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    # Deploy and integrate postgresql if needed
    deploy_postgresql(juju)
    try:
        juju.integrate(app_name, "postgresql-k8s:database")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: status.apps["postgresql-k8s"].is_active, timeout=5 * 60)
    juju.wait(lambda status: status.apps[app_name].is_blocked, timeout=5 * 60)
    return App(app_name)


@pytest.fixture(scope="module", name="fastapi_blocked_app")
def fastapi_blocked_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    fastapi_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the FastAPI charm with non-optional configs using jubilant."""
    app_name = "fastapi-k8s"

    resources = {"app-image": fastapi_app_image}
    charm_file = build_charm_file(
        charm_paths, "fastapi", tmp_path_factory, charm_dict=NON_OPTIONAL_CONFIGS
    )

    try:
        juju.deploy(charm=str(charm_file), app=app_name, resources=resources)
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    # Deploy and integrate postgresql if needed
    deploy_postgresql(juju)
    try:
        juju.integrate(app_name, "postgresql-k8s:database")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: status.apps["postgresql-k8s"].is_active, timeout=5 * 60)
    juju.wait(lambda status: status.apps[app_name].is_blocked, timeout=5 * 60)
    return App(app_name)


@pytest.fixture(scope="module", name="go_blocked_app")
def go_blocked_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    go_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the Go charm with non-optional configs using jubilant."""
    app_name = "go-k8s"

    resources = {"app-image": go_app_image}
    charm_file = build_charm_file(
        charm_paths, "go", tmp_path_factory, charm_dict=NON_OPTIONAL_CONFIGS
    )

    try:
        juju.deploy(charm=str(charm_file), app=app_name, resources=resources)
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    # Deploy and integrate postgresql if needed
    deploy_postgresql(juju)
    try:
        juju.integrate(app_name, "postgresql-k8s:database")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: status.apps["postgresql-k8s"].is_active, timeout=5 * 60)
    juju.wait(lambda status: status.apps[app_name].is_blocked, timeout=5 * 60)
    return App(app_name)


@pytest.fixture(scope="module", name="expressjs_blocked_app")
def expressjs_blocked_app_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    expressjs_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the ExpressJS charm with non-optional configs using jubilant."""
    app_name = "expressjs-k8s"

    resources = {"app-image": expressjs_app_image}
    charm_file = build_charm_file(
        charm_paths, "expressjs", tmp_path_factory, charm_dict=NON_OPTIONAL_CONFIGS
    )

    try:
        juju.deploy(charm=str(charm_file), app=app_name, resources=resources)
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    # Deploy and integrate postgresql if needed
    deploy_postgresql(juju)
    try:
        juju.integrate(app_name, "postgresql-k8s:database")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: status.apps["postgresql-k8s"].is_active, timeout=5 * 60)
    juju.wait(lambda status: status.apps[app_name].is_blocked, timeout=5 * 60)
    return App(app_name)
