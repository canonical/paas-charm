# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""ExpressJS charm unit tests."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

import unittest

import ops
import pytest
from ops.testing import Harness

from .constants import DEFAULT_LAYER, EXPRESSJS_CONTAINER_NAME


@pytest.mark.parametrize(
    "config, env",
    [
        pytest.param(
            {},
            {
                "NODE_ENV": "production",
                "PORT": "8080",
                "APP_BASE_URL": "http://expressjs-k8s.None:8080",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
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
            },
            id="default",
        ),
        pytest.param(
            {
                "node-env": "production",
                "app-secret-key": "foobar",
                "port": 9000,
                "metrics-port": 9001,
                "metrics-path": "/othermetrics",
            },
            {
                "NODE_ENV": "production",
                "PORT": "9000",
                "APP_BASE_URL": "http://expressjs-k8s.None:9000",
                "METRICS_PORT": "9001",
                "METRICS_PATH": "/othermetrics",
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
            },
            id="custom config",
        ),
    ],
)
def test_expressjs_config(harness: Harness, config: dict, env: dict) -> None:
    """
    arrange: none
    act: start the expressjs charm and set expressjs-app container to be ready.
    assert: expressjs charm should submit the correct expressjs pebble layer to pebble.
    """
    container = harness.model.unit.get_container(EXPRESSJS_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.begin_with_initial_hooks()
    harness.charm._secret_storage.get_secret_key = unittest.mock.MagicMock(return_value="test")
    harness.update_config(config)

    assert harness.model.unit.status == ops.ActiveStatus()
    plan = container.get_plan()
    expressjs_layer = plan.to_dict()["services"]["expressjs"]
    assert expressjs_layer == {
        "environment": env,
        "override": "replace",
        "startup": "enabled",
        "command": "npm start",
        "user": "_daemon_",
        "working-dir": "/app",
    }


def test_metrics_config(harness: Harness):
    """
    arrange: Charm with a metrics-endpoint integration
    act: Start the charm with all initial hooks
    assert: The correct port and path for scraping should be in the relation data.
    """

    container = harness.model.unit.get_container(EXPRESSJS_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.add_relation("metrics-endpoint", "prometheus-k8s")
    # update_config has to be executed before begin, as the charm does not call __init__
    # twice in ops and the observability information is updated in __init__.
    harness.update_config({"metrics-port": 9999, "metrics-path": "/metricspath"})

    harness.begin_with_initial_hooks()

    metrics_endpoint_relation = harness.model.relations["metrics-endpoint"]
    assert len(metrics_endpoint_relation) == 1
    relation_data = metrics_endpoint_relation[0].data

    relation_data_unit = relation_data[harness.model.unit]
    assert relation_data_unit["prometheus_scrape_unit_address"]
    assert relation_data_unit["prometheus_scrape_unit_name"] == harness.model.unit.name

    relation_data_app = relation_data[harness.model.app]
    scrape_jobs = relation_data_app["scrape_jobs"]
    assert "/metricspath" in scrape_jobs
    assert "*:9999" in scrape_jobs
