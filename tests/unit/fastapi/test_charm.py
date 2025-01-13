# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""FastAPI charm unit tests."""

import unittest

import ops
import pytest
from ops.testing import Harness

from .constants import DEFAULT_LAYER, FASTAPI_CONTAINER_NAME


@pytest.mark.parametrize(
    "config, postgresql_relation_data, env",
    [
        pytest.param(
            {},
            {},
            {
                "UVICORN_PORT": "8080",
                "WEB_CONCURRENCY": "1",
                "UVICORN_LOG_LEVEL": "info",
                "UVICORN_HOST": "0.0.0.0",
                "APP_BASE_URL": "http://fastapi-k8s.None:8080",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "APP_SECRET_KEY": "test",
            },
            id="default",
        ),
        pytest.param(
            {
                "app-secret-key": "foobar",
                "webserver-port": 9000,
                "metrics-port": 9001,
                "metrics-path": "/othermetrics",
                "user-defined-config": "userdefined",
            },
            {
                "database": "test-database",
                "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
                "password": "test-password",
                "username": "test-username",
            },
            {
                "UVICORN_PORT": "9000",
                "WEB_CONCURRENCY": "1",
                "UVICORN_LOG_LEVEL": "info",
                "UVICORN_HOST": "0.0.0.0",
                "APP_BASE_URL": "http://fastapi-k8s.None:9000",
                "METRICS_PORT": "9001",
                "METRICS_PATH": "/othermetrics",
                "APP_SECRET_KEY": "foobar",
                "APP_USER_DEFINED_CONFIG": "userdefined",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/test-database",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "test-database",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/test-database",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="custom config",
        ),
    ],
)
def test_fastapi_config(
    harness: Harness, config: dict, postgresql_relation_data: dict, env: dict
) -> None:
    """
    arrange: prepare the charm optionally with the postgresql relation.
    act: start the fastapi charm update the config options.
    assert: fastapi charm should submit the correct fastapi pebble layer to pebble.
    """
    container = harness.model.unit.get_container(FASTAPI_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)
    if postgresql_relation_data:
        harness.add_relation("postgresql", "postgresql-k8s", app_data=postgresql_relation_data)

    harness.begin_with_initial_hooks()
    harness.charm._secret_storage.get_secret_key = unittest.mock.MagicMock(return_value="test")
    harness.update_config(config)

    assert harness.model.unit.status == ops.ActiveStatus()
    plan = container.get_plan()
    fastapi_layer = plan.to_dict()["services"]["fastapi"]
    assert fastapi_layer == {
        "environment": env,
        "override": "replace",
        "startup": "enabled",
        "command": "/bin/python3 -m uvicorn app:app",
        "user": "_daemon_",
        "working-dir": "/app",
    }
