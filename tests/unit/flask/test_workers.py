# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scenario tests for Flask worker services."""

import dataclasses

import pytest
from ops import testing

from .constants import DEFAULT_LAYER, LAYER_WITH_WORKER


def _status(name: str, message: str):
    """Build the expected Scenario status."""
    if name == "active":
        return testing.ActiveStatus(message)
    return testing.BlockedStatus(message)


def test_worker(flask_context, base_state, container_name: str) -> None:
    """
    arrange: prepare a unit with worker, scheduler, and unrelated services.
    act: reconcile the charm.
    assert: workers and unit-zero schedulers receive the workload environment.
    """
    container = dataclasses.replace(
        next(iter(base_state["containers"])),
        _base_plan=LAYER_WITH_WORKER,
    )
    state = testing.State(**{**base_state, "containers": {container}})

    out = flask_context.run(flask_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    services = out.get_container(container_name).plan.services
    assert "FLASK_SECRET_KEY" in services["flask"].environment
    assert services["flask"].environment == services["real-worker"].environment
    assert services["flask"].environment == services["Another-Real-WorkeR"].environment
    assert services["real-scheduler"].startup == "enabled"
    assert services["flask"].environment == services["real-scheduler"].environment
    assert services["ANOTHER-REAL-SCHEDULER"].startup == "enabled"
    assert services["flask"].environment == services["ANOTHER-REAL-SCHEDULER"].environment
    assert "FLASK_SECRET_KEY" not in services["not-worker-service"].environment


@pytest.mark.parametrize(
    "flask_layer,worker_class,gevent_result,gunicorn_result,expected_status,expected_message",
    [
        pytest.param(
            DEFAULT_LAYER,
            "eventlet",
            1,
            0,
            "blocked",
            "Only 'gevent' and 'sync' are allowed. https://bit.ly/flask-async-doc",
            id="unsupported-eventlet",
        ),
        pytest.param(
            DEFAULT_LAYER,
            "gevent",
            1,
            0,
            "blocked",
            "gunicorn[gevent] must be installed in the rock. https://bit.ly/flask-async-doc",
            id="missing-gevent",
        ),
        pytest.param(
            {
                **DEFAULT_LAYER,
                "services": {
                    "flask": {
                        "command": "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app"
                    }
                },
            },
            "gevent",
            0,
            0,
            "blocked",
            "Worker class is set through `juju config` but the `-k` worker class argument is not in the service command.",
            id="missing-worker-selector",
        ),
        pytest.param(
            DEFAULT_LAYER,
            "gevent",
            0,
            0,
            "active",
            "",
            id="gevent",
        ),
        pytest.param(
            DEFAULT_LAYER,
            "sync",
            0,
            0,
            "active",
            "",
            id="sync",
        ),
    ],
)
def test_async_workers_config(
    flask_context,
    base_state,
    flask_layer: dict,
    worker_class: str,
    gevent_result: int,
    gunicorn_result: int,
    expected_status: str,
    expected_message: str,
) -> None:
    """
    arrange: configure worker class, Pebble command, and exec outcomes.
    act: reconcile the charm.
    assert: unsupported or unavailable classes block with exact messages.
    """
    container = dataclasses.replace(
        next(iter(base_state["containers"])),
        _base_plan=flask_layer,
        execs={
            testing.Exec(
                ["python3", "-c", "import gevent"],
                return_code=gevent_result,
            ),
            testing.Exec(["/bin/python3"], return_code=gunicorn_result),
        },
    )
    state = testing.State(
        **{
            **base_state,
            "config": {"webserver-worker-class": worker_class},
            "containers": {container},
        }
    )

    out = flask_context.run(flask_context.on.config_changed(), state)

    assert out.unit_status == _status(expected_status, expected_message)
    if expected_status == "active":
        service = out.get_container("app").plan.services["flask"]
        assert f"-k [ {worker_class} ]" in service.command


@pytest.mark.parametrize("flask_context", [{"unit_id": 1}], indirect=True)
def test_worker_multiple_units(flask_context, base_state, container_name: str) -> None:
    """
    arrange: prepare non-leader unit one with three planned units and peer secret data.
    act: reconcile the charm.
    assert: workers run with environment while schedulers are disabled and empty.
    """
    container = dataclasses.replace(
        next(iter(base_state["containers"])),
        _base_plan=LAYER_WITH_WORKER,
    )
    state = testing.State(
        **{
            **base_state,
            "leader": False,
            "planned_units": 3,
            "containers": {container},
        }
    )

    out = flask_context.run(flask_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    services = out.get_container(container_name).plan.services
    assert "FLASK_SECRET_KEY" in services["flask"].environment
    assert services["flask"].environment == services["real-worker"].environment
    assert services["real-scheduler"].startup == "disabled"
    assert "FLASK_SECRET_KEY" not in services["real-scheduler"].environment
    assert services["ANOTHER-REAL-SCHEDULER"].startup == "disabled"
    assert "FLASK_SECRET_KEY" not in services["ANOTHER-REAL-SCHEDULER"].environment
    assert "FLASK_SECRET_KEY" not in services["not-worker-service"].environment
