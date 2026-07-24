# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for worker services."""

import dataclasses

import pytest
from ops import testing

from examples.django.charm.src.charm import DjangoCharm

from .constants import DEFAULT_LAYER


def _status(name: str, message: str):
    """Build the expected Scenario status."""
    if name == "active":
        return testing.ActiveStatus(message)
    return testing.BlockedStatus(message)


@pytest.mark.parametrize(
    "django_layer, worker_class, expected_status, expected_message, exec_res",
    [
        pytest.param(
            DEFAULT_LAYER,
            "eventlet",
            "blocked",
            "Only 'gevent' and 'sync' are allowed. https://bit.ly/django-async-doc",
            1,
            id="fail-eventlet",
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
            "blocked",
            "Worker class is set through `juju config` but the `-k` worker class argument is not in the service command.",
            0,
            id="fail-no-k",
        ),
        pytest.param(
            DEFAULT_LAYER,
            "gevent",
            "active",
            "",
            0,
            id="success-gevent",
        ),
        pytest.param(
            DEFAULT_LAYER,
            "sync",
            "active",
            "",
            0,
            id="success-sync",
        ),
    ],
)
def test_async_workers_config(
    base_state: dict,
    django_layer,
    worker_class,
    expected_status,
    expected_message,
    exec_res,
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
            testing.Exec(["python3", "-c", "import gevent"], return_code=exec_res),
            testing.Exec(["/bin/python3", "-m", "gunicorn"], return_code=exec_res),
        },
    )
    state = testing.State(
        **{
            **base_state,
            "config": {"webserver-worker-class": worker_class},
            "containers": {container},
        }
    )
    context = testing.Context(DjangoCharm)

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == _status(expected_status, expected_message)


@pytest.mark.parametrize(
    "worker_class, expected_status, expected_message, exec_res",
    [
        (
            "eventlet",
            "blocked",
            "Only 'gevent' and 'sync' are allowed. https://bit.ly/django-async-doc",
            1,
        ),
        (
            "gevent",
            "blocked",
            "gunicorn[gevent] must be installed in the rock. https://bit.ly/django-async-doc",
            1,
        ),
        ("sync", "active", "", 0),
    ],
)
def test_async_workers_config_fail(
    base_state: dict,
    worker_class,
    expected_status,
    expected_message,
    exec_res,
):
    """
    arrange: Prepare a unit and run initial hooks.
    act: Set the `webserver-worker-class` config.
    assert: The charm should be blocked if the `webserver-worker-class` config is anything other
    then `sync`.
    """
    container = next(iter(base_state["containers"]))
    container = dataclasses.replace(
        container,
        _base_plan=DEFAULT_LAYER,
        execs={
            testing.Exec(["python3", "-c", "import gevent"], return_code=exec_res),
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
    context = testing.Context(DjangoCharm)

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == _status(expected_status, expected_message)
