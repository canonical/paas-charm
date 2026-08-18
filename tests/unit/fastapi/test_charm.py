# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""FastAPI charm unit tests."""

import json

import pytest
from ops import testing


@pytest.mark.parametrize(
    "config, postgresql_relation_data, env",
    [
        pytest.param(
            {},
            {},
            {
                "APP_NON_OPTIONAL_STRING": "non-optional-value",
                "UVICORN_PORT": "8080",
                "WEB_CONCURRENCY": "1",
                "UVICORN_LOG_LEVEL": "info",
                "UVICORN_HOST": "0.0.0.0",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "APP_BASE_URL": "http://fastapi-k8s.test-model:8080",
                "APP_SECRET_KEY": "test",
                "APP_OIDC_REDIRECT_PATH": "/callback",
                "APP_OIDC_SCOPES": "openid profile email",
                "PYTHONPATH": "/tmp/fastapi/log_config",
                "UVICORN_LOG_CONFIG": "/tmp/fastapi/log_config/uvicorn-log-config.json",
            },
            id="default",
        ),
        pytest.param(
            {
                "app-secret-key": "foobar",
                "user-defined-config": "userdefined",
            },
            {
                "database": "test-database",
                "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
                "password": "test-password",
                "username": "test-username",
            },
            {
                "APP_NON_OPTIONAL_STRING": "non-optional-value",
                "UVICORN_PORT": "8080",
                "WEB_CONCURRENCY": "1",
                "UVICORN_LOG_LEVEL": "info",
                "UVICORN_HOST": "0.0.0.0",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "APP_BASE_URL": "http://fastapi-k8s.test-model:8080",
                "APP_SECRET_KEY": "foobar",
                "APP_USER_DEFINED_CONFIG": "userdefined",
                # pylint: disable=line-too-long
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
                "APP_OIDC_REDIRECT_PATH": "/callback",
                "APP_OIDC_SCOPES": "openid profile email",
                "PYTHONPATH": "/tmp/fastapi/log_config",
                "UVICORN_LOG_CONFIG": "/tmp/fastapi/log_config/uvicorn-log-config.json",
            },
            id="custom config",
        ),
    ],
)
def test_fastapi_config(
    fastapi_context,
    base_state,
    config: dict,
    postgresql_relation_data: dict,
    env: dict,
) -> None:
    """
    arrange: prepare the charm optionally with the postgresql relation.
    act: start the fastapi charm update the config options.
    assert: fastapi charm should submit the correct fastapi pebble layer to pebble.
    """
    if postgresql_relation_data:
        base_state["relations"].append(
            testing.Relation(
                endpoint="postgresql",
                interface="postgresql_client",
                remote_app_data=postgresql_relation_data,
            )
        )
    base_state["config"].update(config)
    state = testing.State(**base_state)

    state_out = fastapi_context.run(fastapi_context.on.config_changed(), state)

    assert state_out.unit_status == testing.ActiveStatus()
    fastapi_layer = state_out.get_container("app").plan.services["fastapi"].to_dict()
    assert fastapi_layer == {
        "environment": env,
        "override": "replace",
        "startup": "enabled",
        "command": "/bin/python3 -m uvicorn app:app",
        "user": "_daemon_",
        "working-dir": "/app",
    }


def test_metrics_config(fastapi_context, base_state) -> None:
    """
    arrange: add a Prometheus scrape relation to the FastAPI state.
    act: start the charm with a config-changed event.
    assert: relation data contains the FastAPI unit and configured workload endpoint.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="metrics-endpoint",
            interface="prometheus_scrape",
        )
    )
    state = testing.State(**base_state)

    state_out = fastapi_context.run(fastapi_context.on.config_changed(), state)

    assert state_out.unit_status == testing.ActiveStatus()
    metrics_relations = state_out.get_relations("metrics-endpoint")
    assert len(metrics_relations) == 1
    assert metrics_relations[0].local_unit_data["prometheus_scrape_unit_address"]
    assert metrics_relations[0].local_unit_data["prometheus_scrape_unit_name"] == "fastapi-k8s/0"
    assert json.loads(metrics_relations[0].local_app_data["scrape_jobs"]) == [
        {
            "metrics_path": "/metrics",
            "static_configs": [{"targets": ["*:8080"]}],
        }
    ]
