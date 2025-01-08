# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for worker services."""

import copy
import unittest.mock
from secrets import token_hex

import ops
import pytest
from ops.testing import ExecResult, Harness

from .constants import DEFAULT_LAYER, FLASK_CONTAINER_NAME, LAYER_WITH_WORKER


def test_worker(harness: Harness):
    """
    arrange: Prepare a unit with workers and schedulers.
    act: Run initial hooks.
    assert: The workers should have all the environment variables. Also the schedulers, as
            the unit is 0.
    """
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    flask_layer = copy.deepcopy(LAYER_WITH_WORKER)
    container.add_layer("a_layer", LAYER_WITH_WORKER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    services = container.get_plan().services
    assert "FLASK_SECRET_KEY" in services["flask"].environment
    assert services["flask"].environment == services["real-worker"].environment
    assert services["flask"].environment == services["Another-Real-WorkeR"].environment
    assert services["real-scheduler"].startup == "enabled"
    assert services["flask"].environment == services["real-scheduler"].environment
    assert services["ANOTHER-REAL-SCHEDULER"].startup == "enabled"
    assert services["flask"].environment == services["ANOTHER-REAL-SCHEDULER"].environment
    assert "FLASK_SECRET_KEY" not in services["not-worker-service"].environment


@pytest.mark.parametrize(
    "worker_class, expected_status, expected_message, exec_res",
    [
        (
            "eventlet",
            "blocked",
            "Only 'gevent' and 'sync' are allowed. https://bit.ly/flask-async-doc",
            1,
        ),
        ("gevent", "active", "", 0),
        ("sync", "active", "", 0),
    ],
)
def test_async_workers_config(
    harness: Harness, worker_class, expected_status, expected_message, exec_res
):
    """
    arrange: Prepare a unit and run initial hooks.
    act: Set the `webserver-worker-class` config.
    assert: The charm should be blocked if the `webserver-worker-class` config is anything other
    then `sync` or `gevent`.
    """
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.handle_exec(
        container.name,
        ["python3", "-c", "import gevent"],
        result=ExecResult(exit_code=exec_res),
    )

    harness.begin_with_initial_hooks()
    harness.update_config({"webserver-worker-class": worker_class})
    assert harness.model.unit.status == ops.StatusBase.from_name(
        name=expected_status, message=expected_message
    )


@pytest.mark.parametrize(
    "worker_class, expected_status, expected_message, exec_res",
    [
        (
            "eventlet",
            "blocked",
            "Only 'gevent' and 'sync' are allowed. https://bit.ly/flask-async-doc",
            1,
        ),
        (
            "gevent",
            "blocked",
            "gunicorn[gevent] must be installed in the rock. https://bit.ly/flask-async-doc",
            1,
        ),
        ("sync", "active", "", 0),
    ],
)
def test_async_workers_config_fail(
    harness: Harness, worker_class, expected_status, expected_message, exec_res
):
    """
    arrange: Prepare a unit and run initial hooks.
    act: Set the `webserver-worker-class` config.
    assert: The charm should be blocked if the `webserver-worker-class` config is anything other
    then `sync`.
    """
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.handle_exec(
        container.name,
        ["python3", "-c", "import gevent"],
        result=ExecResult(exit_code=exec_res),
    )
    harness.begin_with_initial_hooks()
    harness.update_config({"webserver-worker-class": worker_class})
    assert harness.model.unit.status == ops.StatusBase.from_name(
        name=expected_status, message=expected_message
    )


def test_worker_multiple_units(harness: Harness):
    """
    arrange: Prepare a unit with workers that is not the first one (number 1)
    act: Run initial hooks.
    assert: The workers should have all the environment variables. The schedulers should be
            disabled and not have the environment variables
    """

    # This is tricky and could be problematic
    harness.framework.model.unit.name = f"{harness._meta.name}/1"
    harness.set_planned_units(3)

    # Just think that we are not the leader unit. For this it is necessary to put data
    # in the peer relation for the secret..
    harness.set_leader(False)
    harness.add_relation(
        "secret-storage", harness.framework.model.app.name, app_data={"flask_secret_key": "XX"}
    )

    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", LAYER_WITH_WORKER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    services = container.get_plan().services
    assert "FLASK_SECRET_KEY" in services["flask"].environment
    assert services["flask"].environment == services["real-worker"].environment
    assert services["real-scheduler"].startup == "disabled"
    assert "FLASK_SECRET_KEY" not in services["real-scheduler"].environment
    assert "FLASK_SECRET_KEY" not in services["not-worker-service"].environment
