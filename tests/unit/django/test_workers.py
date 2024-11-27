# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for worker services."""

import ops
import pytest
from ops.testing import Harness

from .constants import DEFAULT_LAYER


@pytest.mark.parametrize(
    "worker_class, expected_status, expected_message",
    [
        (
            "eventlet",
            "blocked",
            "Only 'gevent' and 'sync' are allowed. https://bit.ly/django-async-doc",
        ),
        ("gevent", "active", ""),
        ("sync", "active", ""),
    ],
)
def test_async_workers_config(harness: Harness, worker_class, expected_status, expected_message):
    """
    arrange: Prepare a unit and run initial hooks.
    act: Set the `webserver-worker-class` config.
    assert: The charm should be blocked if the `webserver-worker-class` config is anything other
    then `sync` or `gevent`.
    """
    postgresql_relation_data = {
        "database": "test-database",
        "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
        "password": "test-password",
        "username": "test-username",
    }
    harness.add_relation("postgresql", "postgresql-k8s", app_data=postgresql_relation_data)
    container = harness.model.unit.get_container("django-app")
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.handle_exec(
        container.name,
        ["python3", "-c", "'import gevent;print(gevent.__version__)'"],
        result="Gevent",
    )
    harness.begin_with_initial_hooks()
    harness.update_config({"webserver-worker-class": worker_class})
    assert harness.model.unit.status == ops.StatusBase.from_name(
        name=expected_status, message=expected_message
    )


@pytest.mark.parametrize(
    "worker_class, expected_status, expected_message",
    [
        (
            "eventlet",
            "blocked",
            "Only 'gevent' and 'sync' are allowed. https://bit.ly/django-async-doc",
        ),
        (
            "gevent",
            "blocked",
            "gunicorn[gevent] must be installed in the rock. https://bit.ly/django-async-doc",
        ),
        ("sync", "active", ""),
    ],
)
def test_async_workers_config_fail(
    harness: Harness, worker_class, expected_status, expected_message
):
    """
    arrange: Prepare a unit and run initial hooks.
    act: Set the `webserver-worker-class` config.
    assert: The charm should be blocked if the `webserver-worker-class` config is anything other
    then `sync`.
    """
    postgresql_relation_data = {
        "database": "test-database",
        "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
        "password": "test-password",
        "username": "test-username",
    }
    harness.add_relation("postgresql", "postgresql-k8s", app_data=postgresql_relation_data)
    container = harness.model.unit.get_container("django-app")
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.handle_exec(
        container.name,
        ["python3", "-c", "'import gevent;print(gevent.__version__)'"],
        result="ModuleNotFoundError",
    )
    harness.begin_with_initial_hooks()
    harness.update_config({"webserver-worker-class": worker_class})
    assert harness.model.unit.status == ops.StatusBase.from_name(
        name=expected_status, message=expected_message
    )
