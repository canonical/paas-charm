# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for worker services."""

import dataclasses

import pytest
from ops import testing

from .constants import DEFAULT_LAYER


def _status(name: str, message: str):
    """Build the expected Scenario status."""
    if name == "active":
        return testing.ActiveStatus(message)
    return testing.BlockedStatus(message)


@pytest.mark.parametrize(
    "django_layer,worker_class,gevent_result,expected_status,expected_message",
    [
        pytest.param(
            DEFAULT_LAYER,
            "eventlet",
            1,
            "blocked",
            "Only 'gevent' and 'sync' are allowed. https://bit.ly/django-async-doc",
            id="unsupported-eventlet",
        ),
        pytest.param(
            DEFAULT_LAYER,
            "gevent",
            1,
            "blocked",
            "gunicorn[gevent] must be installed in the rock. https://bit.ly/django-async-doc",
            id="missing-gevent",
        ),
        pytest.param(
            {
                **DEFAULT_LAYER,
                "services": {
                    "django": {
                        "command": "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application"
                    }
                },
            },
            "gevent",
            0,
            "blocked",
            "Worker class is set through `juju config` but the `-k` worker class argument is not in the service command.",
            id="missing-worker-selector",
        ),
        pytest.param(
            DEFAULT_LAYER,
            "gevent",
            0,
            "active",
            "",
            id="gevent",
        ),
        pytest.param(
            DEFAULT_LAYER,
            "sync",
            0,
            "active",
            "",
            id="sync",
        ),
    ],
)
def test_async_workers_config(
    django_context,
    base_state: dict,
    django_layer,
    worker_class,
    gevent_result,
    expected_status,
    expected_message,
):
    """
    arrange: Prepare a unit and run initial hooks.
    act: Set the `webserver-worker-class` config.
    assert: The charm should be blocked if the `webserver-worker-class` config is anything other
    then `sync` or `gevent`.
    """
    container = next(iter(base_state["containers"]))
    container = dataclasses.replace(
        container,
        _base_plan=django_layer,
        execs={
            testing.Exec(["python3", "-c", "import gevent"], return_code=gevent_result),
            testing.Exec(["/bin/python3"], return_code=0),
        },
    )
    state = testing.State(
        **{
            **base_state,
            "config": {"webserver-worker-class": worker_class},
            "containers": {container},
        }
    )

    out = django_context.run(django_context.on.config_changed(), state)

    assert out.unit_status == _status(expected_status, expected_message)
    if expected_status == "active":
        service = out.get_container("app").plan.services["django"]
        assert f"-k [ {worker_class} ]" in service.command
