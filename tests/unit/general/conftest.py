# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""pytest fixtures for the go unit test."""

import os
import pathlib
import typing

import ops
import pytest
from ops.testing import Harness

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from src.paas_charm.charm import PaasCharm
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

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(name="expressjs_harness")
def expressjs_harness_fixture() -> typing.Generator[Harness, None, None]:
    """ExpressJS harness fixture."""
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
    os.chdir(PROJECT_ROOT / "examples/flask")
    harness = _build_harness(FlaskCharm, FLASK_CONTAINER_NAME, FLASK_DEFAULT_LAYER, "flask/app")
    _set_check_config_handler(harness, "flask", FLASK_CONTAINER_NAME, FLASK_DEFAULT_LAYER)

    yield harness

    harness.cleanup()


@pytest.fixture(name="fastapi_harness")
def fastapi_harness_fixture() -> typing.Generator[Harness, None, None]:
    """FastAPI harness fixture."""
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
