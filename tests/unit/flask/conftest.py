# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pytest fixtures local to the Flask unit tests."""

import pathlib

import pytest

from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config


@pytest.fixture(name="base_state")
def base_state_fixture(flask_framework_state):
    """Expose the focused Flask state under the framework-local name."""
    return flask_framework_state


@pytest.fixture(name="webserver")
def webserver_fixture(flask_container_mock):
    """Return a Gunicorn webserver backed by the focused container mock."""
    workload_config = create_workload_config(
        framework_name="flask",
        unit_name="flask/0",
        state_dir=pathlib.Path("/tmp/flask/state"),
    )
    return GunicornWebserver(
        webserver_config=WebserverConfig(),
        workload_config=workload_config,
        container=flask_container_mock,
    )
