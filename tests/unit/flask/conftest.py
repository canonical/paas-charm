# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the integration test."""
import os
import pathlib
import shlex
import typing

import ops
import pytest
from ops.testing import Harness

from examples.flask.src.charm import FlaskCharm

from .constants import DEFAULT_LAYER, FLASK_CONTAINER_NAME

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/flask")


@pytest.fixture(name="harness")
def harness_fixture() -> typing.Generator[Harness, None, None]:
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
        *[
            x
            for x in shlex.split(DEFAULT_LAYER["services"]["flask"]["command"])
            if x not in ["[", "]"]
        ],
        "--check-config",
    ]
    harness.handle_exec(
        FLASK_CONTAINER_NAME,
        check_config_command,
        handler=check_config_handler,
    )

    gevent_check_config_command = ["gevent" if x == "sync" else x for x in check_config_command]
    harness.handle_exec(
        FLASK_CONTAINER_NAME,
        gevent_check_config_command,
        handler=check_config_handler,
    )

    yield harness
    harness.cleanup()
