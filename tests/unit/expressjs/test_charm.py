# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""ExpressJS charm unit tests."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

import pytest
from ops import testing

from examples.expressjs.charm.src.charm import ExpressJSCharm


@pytest.mark.parametrize(
    "config, env",
    [
        pytest.param(
            {},
            {
                "NODE_ENV": "production",
                "PORT": "8080",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "APP_BASE_URL": "http://expressjs-k8s.test-model:8080",
                "APP_SECRET_KEY": "test",
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
            },
            id="default",
        ),
        pytest.param(
            {
                "node-env": "production",
                "app-secret-key": "foobar",
            },
            {
                "NODE_ENV": "production",
                "PORT": "8080",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "APP_BASE_URL": "http://expressjs-k8s.test-model:8080",
                "APP_SECRET_KEY": "foobar",
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
            },
            id="custom config",
        ),
    ],
)
def test_expressjs_config(base_state, config: dict, env: dict) -> None:
    """
    arrange: none
    act: start the expressjs charm and set expressjs-app container to be ready.
    assert: expressjs charm should submit the correct expressjs pebble layer to pebble.
    """
    base_state["config"] = config
    state = testing.State(**base_state)
    context = testing.Context(charm_type=ExpressJSCharm)
    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    expressjs_layer = out.get_container("app").plan.services["expressjs"].to_dict()
    assert expressjs_layer == {
        "environment": env,
        "override": "replace",
        "startup": "enabled",
        "command": "npm start",
        "user": "_daemon_",
        "working-dir": "/app",
    }


def test_metrics_config(base_state) -> None:
    """
    arrange: Charm with a metrics-endpoint integration
    act: Start the charm with all initial hooks
    assert: The correct port and path for scraping should be in the relation data.
    """

    base_state["relations"].append(
        testing.Relation(
            endpoint="metrics-endpoint",
            interface="prometheus_scrape",
        )
    )
    state = testing.State(**base_state)
    context = testing.Context(charm_type=ExpressJSCharm)

    out = context.run(context.on.config_changed(), state)

    metrics_endpoint_relations = out.get_relations("metrics-endpoint")
    assert len(metrics_endpoint_relations) == 1

    relation_data_unit = metrics_endpoint_relations[0].local_unit_data
    assert relation_data_unit["prometheus_scrape_unit_address"]
    assert relation_data_unit["prometheus_scrape_unit_name"] == "expressjs-k8s/0"

    scrape_jobs = metrics_endpoint_relations[0].local_app_data["scrape_jobs"]
    assert "/metrics" in scrape_jobs
    assert "*:8080" in scrape_jobs
