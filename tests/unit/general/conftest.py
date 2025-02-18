"""pytest fixtures for the go unit test."""

import os
import pathlib
import shlex
import typing

import ops
import pytest
from ops.testing import Harness

from examples.django.charm.src.charm import DjangoCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from tests.unit.django.constants import DJANGO_CONTAINER_NAME
from tests.unit.fastapi.constants import FASTAPI_CONTAINER_NAME
from tests.unit.flask.constants import DEFAULT_LAYER as FLASK_DEFAULT_LAYER
from tests.unit.flask.constants import FLASK_CONTAINER_NAME
from tests.unit.go.constants import DEFAULT_LAYER as GO_DEFAULT_LAYER
from tests.unit.go.constants import GO_CONTAINER_NAME

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

MOCK_YAML = {
    "options": {
        (non_optional_config_name_1 := "bool"): {"type": "boolean", "optional": False},
        (config_name_1 := "optional-bool"): {"type": "boolean", "optional": True},
        (non_optional_config_name_2 := "int"): {"type": "int", "optional": False},
        (config_name_2 := "optional-int"): {"type": "int", "optional": True},
        (non_optional_config_name_3 := "float"): {"type": "float", "optional": False},
        (config_name_3 := "optional-float"): {"type": "float", "optional": True},
        (non_optional_config_name_4 := "str"): {"type": "string", "optional": False},
        (config_name_4 := "optional-str"): {"type": "string", "optional": True},
        (non_optional_config_name_5 := "secret"): {"type": "secret", "optional": False},
    }
}

NON_OPTIONAL_CONFIGS = [
    non_optional_config_name_1,
    non_optional_config_name_2,
    non_optional_config_name_3,
    non_optional_config_name_4,
]


OPTIONAL_CONFIGS = [config_name_1, config_name_2, config_name_3, config_name_4]


# @pytest.fixture(autouse=True, scope="package")
# def cwd():
#     return os.chdir(PROJECT_ROOT / "examples/go/charm")


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/flask")


@pytest.fixture(name="go_harness")
def go_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(GoCharm)
    harness.set_leader()
    root = harness.get_filesystem_root(GO_CONTAINER_NAME)
    (root / "app").mkdir(parents=True)
    harness.set_can_connect(GO_CONTAINER_NAME, True)
    harness.begin_with_initial_hooks()

    container = harness.model.unit.get_container(GO_CONTAINER_NAME)
    container.add_layer("a_layer", GO_DEFAULT_LAYER)
    yield harness
    harness.cleanup()


@pytest.fixture(name="flask_harness")
def flask_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(FlaskCharm)
    harness.set_leader()
    root = harness.get_filesystem_root(FLASK_CONTAINER_NAME)
    (root / "flask/app").mkdir(parents=True)
    harness.set_can_connect(FLASK_CONTAINER_NAME, True)

    def check_config_handler(_):
        """Handle the gunicorn check config command."""
        config_file = root / "flask/gunicorn.conf.py"
        if config_file.is_file():
            return ops.testing.ExecResult(0)
        return ops.testing.ExecResult(1)

    check_config_command = [
        *shlex.split(FLASK_DEFAULT_LAYER["services"]["flask"]["command"].split("-k")[0]),
        "--check-config",
    ]
    harness.handle_exec(
        FLASK_CONTAINER_NAME,
        check_config_command,
        handler=check_config_handler,
    )
    harness.begin_with_initial_hooks()
    container = harness.charm.unit.get_container(FLASK_CONTAINER_NAME)
    # ops.testing framework apply layers by label in lexicographical order...
    container.add_layer("a_layer", FLASK_DEFAULT_LAYER)
    yield harness
    harness.cleanup()


@pytest.fixture(name="fastapi_harness")
def fastapi_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(FastAPICharm)
    harness.set_leader()
    root = harness.get_filesystem_root(FASTAPI_CONTAINER_NAME)
    (root / "app").mkdir(parents=True)
    harness.set_can_connect(FASTAPI_CONTAINER_NAME, True)

    yield harness
    harness.cleanup()


@pytest.fixture(name="django_harness")
def django_harness_fixture() -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(DjangoCharm)
    harness.set_leader()
    root = harness.get_filesystem_root(DJANGO_CONTAINER_NAME)
    (root / "django/app").mkdir(parents=True)
    harness.set_can_connect(DJANGO_CONTAINER_NAME, True)

    yield harness
    harness.cleanup()
