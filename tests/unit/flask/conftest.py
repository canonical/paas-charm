# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the integration test."""
import os
import pathlib
import shlex
import typing
import unittest.mock

import ops
import pytest
from ops.testing import Harness

from examples.flask.src.charm import FlaskCharm
from paas_charm.database_migration import DatabaseMigrationStatus

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
        *shlex.split(DEFAULT_LAYER["services"]["flask"]["command"]),
        "--check-config",
    ]
    harness.handle_exec(
        FLASK_CONTAINER_NAME,
        check_config_command,
        handler=check_config_handler,
    )

    yield harness
    harness.cleanup()


@pytest.fixture
def database_migration_mock():
    """Create a mock instance for the DatabaseMigration class."""
    mock = unittest.mock.MagicMock()
    mock.status = DatabaseMigrationStatus.PENDING
    mock.script = None
    return mock
