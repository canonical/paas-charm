# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""pytest fixtures for the go unit test."""

import os
import pathlib
import shutil
import typing

import ops
import pytest
import yaml
from ops import testing
from ops.testing import Harness

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from src.paas_charm.charm import PaasCharm
from tests.unit.conftest import postgresql_relation
from tests.unit.django.constants import DEFAULT_LAYER as DJANGO_DEFAULT_LAYER
from tests.unit.django.constants import DJANGO_CONTAINER_NAME
from tests.unit.expressjs.constants import DEFAULT_LAYER as EXPRESSJS_DEFAULT_LAYER
from tests.unit.expressjs.constants import EXPRESSJS_CONTAINER_NAME
from tests.unit.fastapi.constants import DEFAULT_LAYER as FASTAPI_DEFAULT_LAYER
from tests.unit.fastapi.constants import FASTAPI_CONTAINER_NAME
from tests.unit.flask.constants import DEFAULT_LAYER as FLASK_DEFAULT_LAYER
from tests.unit.flask.constants import FLASK_CONTAINER_NAME
from tests.unit.go.constants import DEFAULT_LAYER as GO_DEFAULT_LAYER
from tests.unit.go.constants import GO_CONTAINER_NAME
from tests.unit.test_charm.src.charm import TestCharm

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

TEST_CONTAINER_NAME = "app"
TEST_DEFAULT_LAYER = {
    "services": {
        "app": {
            "override": "replace",
            "startup": "enabled",
            "command": "test-command",
            "user": "_daemon_",
        }
    }
}


@pytest.fixture(name="generic_harness")
def generic_harness_fixture():
    """Generic charm harness for testing."""
    os.chdir(PROJECT_ROOT / "tests/unit/test_charm")
    harness = _build_harness(TestCharm, TEST_CONTAINER_NAME, TEST_DEFAULT_LAYER, "app")
    harness.begin()
    return harness


@pytest.fixture(name="expressjs_harness")
def expressjs_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Express JS harness fixture."""
    os.chdir(PROJECT_ROOT / "examples/expressjs/charm")
    harness = _build_harness(
        ExpressJSCharm, EXPRESSJS_CONTAINER_NAME, EXPRESSJS_DEFAULT_LAYER, "app"
    )

    postgresql_relation_data = {
        "database": "test-database",
        "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
        "password": "test-password",
        "username": "test-username",
    }
    harness.add_relation("postgresql", "postgresql-k8s", app_data=postgresql_relation_data)
    yield harness

    harness.cleanup()


@pytest.fixture(name="go_harness")
def go_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Go harness fixture."""
    os.chdir(PROJECT_ROOT / "examples/go/charm")
    harness = _build_harness(GoCharm, GO_CONTAINER_NAME, GO_DEFAULT_LAYER, "app")

    yield harness

    harness.cleanup()


@pytest.fixture(name="flask_harness")
def flask_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Flask harness fixture."""
    os.chdir(PROJECT_ROOT / "examples/flask/charm")
    harness = _build_harness(FlaskCharm, FLASK_CONTAINER_NAME, FLASK_DEFAULT_LAYER, "flask/app")
    _set_check_config_handler(harness, "flask", FLASK_CONTAINER_NAME, FLASK_DEFAULT_LAYER)

    yield harness

    harness.cleanup()


@pytest.fixture(name="fastapi_harness")
def fastapi_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Fast API harness fixture."""
    os.chdir(PROJECT_ROOT / "examples/fastapi/charm")
    harness = _build_harness(FastAPICharm, FASTAPI_CONTAINER_NAME, FASTAPI_DEFAULT_LAYER, "app")

    harness.update_config({"non-optional-string": ""})
    yield harness

    harness.cleanup()


@pytest.fixture(name="django_harness")
def django_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Django harness fixture."""
    os.chdir(PROJECT_ROOT / "examples/django/charm")
    harness = _build_harness(
        DjangoCharm, DJANGO_CONTAINER_NAME, DJANGO_DEFAULT_LAYER, "django/app"
    )
    _set_check_config_handler(harness, "django", DJANGO_CONTAINER_NAME, DJANGO_DEFAULT_LAYER)

    postgresql_relation_data = {
        "database": "test-database",
        "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
        "password": "test-password",
        "username": "test-username",
    }
    harness.add_relation("postgresql", "postgresql-k8s", app_data=postgresql_relation_data)

    yield harness

    harness.cleanup()


def _build_harness(charm: PaasCharm, container_name: str, layer: dict, folder: str) -> Harness:
    """Build the harness for specific framework.

    Args:
        charm: Charm to build harness for.
        container_name: Container name of the charm.
        layer: Default layer for the charm.
        folder: Folder name of the workload in the container.

    Returns:
        The harness built for the charm.
    """
    harness = Harness(charm)
    harness.set_leader()
    root = harness.get_filesystem_root(container_name)
    (root / folder).mkdir(parents=True)
    harness.set_can_connect(container_name, True)
    container = harness.model.unit.get_container(container_name)
    container.add_layer("a_layer", layer)
    return harness


def _set_check_config_handler(
    harness: Harness, framework: str, container_name: str, layer: dict
) -> None:
    """Set the check_config handler for Flask and Django workloads.

    Args:
        harness: Charms harness.
        framework: Framework of the charm.
        container_name: Container name of the charm.
        layer: Default layer for the charm.
    """

    def check_config_handler(_):
        """Handle the gunicorn check config command."""
        config_file = harness.get_filesystem_root(container_name) / f"{framework}/gunicorn.conf.py"
        if config_file.is_file():
            return ops.testing.ExecResult(0)
        return ops.testing.ExecResult(1)

    check_config_command = [
        "/bin/python3",
        "-m",
        "gunicorn",
        "-c",
        f"/{framework}/gunicorn.conf.py",
        "app:app" if framework == "flask" else "django_app.wsgi:application",
        "-k",
        "sync",
        "--check-config",
    ]
    harness.handle_exec(
        container_name,
        check_config_command,
        handler=check_config_handler,
    )


@pytest.fixture(scope="function", name="flask_base_state")
def flask_base_state_fixture():
    """State with container and config file set."""
    os.chdir(PROJECT_ROOT / "examples/flask/charm")
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"flask_secret_key": "test", "secret": "test"}
            ),
        ],
        "containers": {
            testing.Container(
                name="flask-app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/flask/gunicorn.conf.py", source="conf")},
                execs={
                    testing.Exec(
                        command_prefix=["/bin/python3"],
                        return_code=0,
                    ),
                },
                _base_plan={
                    "services": {
                        "flask": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app -k [ sync ]",
                        }
                    }
                },
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(scope="function", name="spring_boot_base_state")
def spring_boot_state_fixture():
    """State with container and config file set."""
    os.chdir(PROJECT_ROOT / "examples/springboot/charm")
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"spring-boot_secret_key": "test"}
            ),
            postgresql_relation("spring-boot-k8s"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/app/saml.cert", source="cert")},
                _base_plan={
                    "services": {
                        "spring-boot": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": 'bash -c "java -jar *.jar"',
                        }
                    }
                },
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(scope="function", name="multiple_oauth_integrations")
def multiple_oauth_integrations_fixture(request):
    os.chdir(PROJECT_ROOT / f"examples/{request.param.get('framework')}/charm")
    shutil.copy("charmcraft.yaml", "org_charmcraft.yaml")
    charmcraft_yaml = yaml.safe_load(open("charmcraft.yaml", "r").read())
    charmcraft_yaml["requires"]["google"] = {"interface": "oauth", "optional": True, "limit": 1}
    charmcraft_yaml["config"]["options"]["google-redirect-path"] = {
        "default": "/callback",
        "description": "The path that the user will be redirected upon completing login.",
        "type": "string",
    }
    charmcraft_yaml["config"]["options"]["google-scopes"] = {
        "default": "openid profile email",
        "description": "A list of scopes with spaces in between.",
        "type": "string",
    }
    charmcraft_yaml["config"]["options"]["google-user-name-attribute"] = {
        "default": "email",
        "description": "The name of the attribute returned in the UserInfo Response that references the Name or Identifier of the end-user.",
        "type": "string",
    }
    yaml.safe_dump(charmcraft_yaml, open("charmcraft.yaml", "w"))

    yield

    shutil.copyfile("org_charmcraft.yaml", "charmcraft.yaml")
    os.remove("org_charmcraft.yaml")


@pytest.fixture(scope="function", name="django_base_state")
def django_base_state_fixture():
    """State with container and config file set."""
    os.chdir(PROJECT_ROOT / "examples/django/charm")
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"django_secret_key": "test", "secret": "test"}
            ),
            postgresql_relation("django-k8s"),
        ],
        "containers": {
            testing.Container(
                name="django-app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/django/gunicorn.conf.py", source="conf")},
                execs={
                    testing.Exec(
                        command_prefix=["/bin/python3"],
                        return_code=0,
                    ),
                },
                _base_plan={
                    "services": {
                        "django": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application -k [ sync ]",
                        }
                    }
                },
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(scope="function", name="fastapi_base_state")
def fastapi_base_state_fixture():
    """State with container and config file set."""
    os.chdir(PROJECT_ROOT / "examples/fastapi/charm")
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"fastapi_secret_key": "test", "secret": "test"}
            ),
            postgresql_relation("fastapi-k8s"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["/bin/python3"],
                        return_code=0,
                    ),
                },
                _base_plan={
                    "services": {
                        "fastapi": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/bin/python3 -m uvicorn app:app",
                        }
                    }
                },
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(scope="function", name="go_base_state")
def go_base_state_fixture():
    """State with container and config file set."""
    os.chdir(PROJECT_ROOT / "examples/go/charm")
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"go_secret_key": "test", "secret": "test"}
            ),
            postgresql_relation("go-k8s"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                execs={
                    testing.Exec(
                        command_prefix=["go-app"],
                        return_code=0,
                    ),
                },
                _base_plan={
                    "services": {
                        "go": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "go-app",
                        }
                    }
                },
            )
        },
        "model": testing.Model(name="test-model"),
    }


OAUTH_RELATION_DATA_EXAMPLE = {
    "authorization_endpoint": "https://traefik_ip/model_name-hydra/oauth2/auth",
    "introspection_endpoint": "http://hydra.model_name.svc.cluster.local:4445/admin/oauth2/introspect",
    "issuer_url": "https://traefik_ip/model_name-hydra",
    "jwks_endpoint": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
    "scope": "openid profile email",
    "token_endpoint": "https://traefik_ip/model_name-hydra/oauth2/token",
    "userinfo_endpoint": "https://traefik_ip/model_name-hydra/userinfo",
    "client_id": "test-client-id",
}
