# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go charm unit tests."""

import unittest

import ops
import pytest
from ops.testing import Harness

from .constants import DEFAULT_LAYER, GO_CONTAINER_NAME


@pytest.mark.parametrize(
    "config, env",
    [
        pytest.param(
            {},
            {
                "APP_PORT": "8080",
                "APP_BASE_URL": "http://go-k8s.None:8080",
                "APP_METRICS_PORT": "8080",
                "APP_METRICS_PATH": "/metrics",
                "APP_SECRET_KEY": "test",
                "APP_OIDC_REDIRECT_PATH": "/auth/openid-connect/callback",
                "APP_OIDC_SCOPES": "openid profile email",
            },
            id="default",
        ),
        pytest.param(
            {
                "app-secret-key": "foobar",
                "app-port": 9000,
                "metrics-port": 9001,
                "metrics-path": "/othermetrics",
            },
            {
                "APP_PORT": "9000",
                "APP_BASE_URL": "http://go-k8s.None:9000",
                "APP_METRICS_PORT": "9001",
                "APP_METRICS_PATH": "/othermetrics",
                "APP_SECRET_KEY": "foobar",
                "APP_OIDC_REDIRECT_PATH": "/auth/openid-connect/callback",
                "APP_OIDC_SCOPES": "openid profile email",
            },
            id="custom config",
        ),
    ],
)
def test_go_config(harness: Harness, config: dict, env: dict) -> None:
    """
    arrange: none
    act: start the go charm and set go-app container to be ready.
    assert: go charm should submit the correct go pebble layer to pebble.
    """
    container = harness.model.unit.get_container(GO_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.begin_with_initial_hooks()
    harness.charm._secret_storage.get_secret_key = unittest.mock.MagicMock(return_value="test")
    harness.update_config(config)

    assert harness.model.unit.status == ops.ActiveStatus()
    plan = container.get_plan()
    go_layer = plan.to_dict()["services"]["go"]
    assert go_layer == {
        "environment": env,
        "override": "replace",
        "startup": "enabled",
        "command": "/usr/local/bin/go-k8s",
        "user": "_daemon_",
        "working-dir": "/app",
    }


def test_metrics_config(harness: Harness):
    """
    arrange: Charm with a metrics-endpoint integration
    act: Start the charm with all initial hooks
    assert: The correct port and path for scraping should be in the relation data.
    """
    container = harness.model.unit.get_container(GO_CONTAINER_NAME)
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
