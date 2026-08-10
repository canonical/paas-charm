# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the integration test."""

import os
import pathlib
import typing

import ops
import pytest
from ops.testing import Harness

from examples.flask.charm.src.charm import FlaskCharm
from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/flask/charm")


@pytest.fixture(name="harness")
def harness_fixture(container_name: str) -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(FlaskCharm)
    harness.set_leader()
    root = harness.get_filesystem_root(container_name)
    (root / "flask/app").mkdir(parents=True)
    harness.set_can_connect(container_name, True)

    def check_config_handler(_):
        """Handle the gunicorn check config command."""
        config_file = root / "flask/gunicorn.conf.py"
        if config_file.is_file():
            return ops.testing.ExecResult(0)
        return ops.testing.ExecResult(1)

    check_config_command = [
        "/bin/python3",
        "-m",
        "gunicorn",
        "-c",
        "/flask/gunicorn.conf.py",
        "app:app",
        "-k",
        "sync",
        "--check-config",
    ]
    harness.handle_exec(
        container_name,
        check_config_command,
        handler=check_config_handler,
    )

    gevent_check_config_command = [
        "/bin/python3",
        "-m",
        "gunicorn",
        "-c",
        "/flask/gunicorn.conf.py",
        "app:app",
        "-k",
        "gevent",
        "--check-config",
    ]
    harness.handle_exec(
        container_name,
        gevent_check_config_command,
        handler=check_config_handler,
    )

    yield harness
    harness.cleanup()


@pytest.fixture(name="webserver")
def webserver_fixture(flask_container_mock):
    workload_config = create_workload_config(
        framework_name="flask", unit_name="flask/0", state_dir=pathlib.Path("/tmp/flask/state")
    )
    return GunicornWebserver(
        webserver_config=WebserverConfig(),
        workload_config=workload_config,
        container=flask_container_mock,
    )
