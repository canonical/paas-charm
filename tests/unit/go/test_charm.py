# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go charm unit tests."""

import pytest
from ops import testing

from examples.go.charm.src.charm import GoCharm


@pytest.mark.parametrize(
    "config, env",
    [
        pytest.param(
            {},
            {
                "APP_PORT": "8080",
                "APP_BASE_URL": "http://go-k8s.test-model:8080",
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
                "APP_BASE_URL": "http://go-k8s.test-model:9000",
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
def test_go_config(base_state, config: dict, env: dict) -> None:
    """
    arrange: none
    act: start the go charm and set go-app container to be ready.
    assert: go charm should submit the correct go pebble layer to pebble.
    """
    base_state["config"] = config
    state = testing.State(**base_state)
    context = testing.Context(charm_type=GoCharm)
    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    go_layer = out.get_container("app").plan.services["go"].to_dict()
    assert go_layer == {
        "environment": env,
        "override": "replace",
        "startup": "enabled",
        "command": "/usr/local/bin/go-k8s",
        "user": "_daemon_",
        "working-dir": "/app",
    }


def test_metrics_config(base_state) -> None:
    """
    arrange: Charm with a metrics-endpoint integration
    act: Start the charm with all initial hooks
    assert: The correct port and path for scraping should be in the relation data.
    """
    base_state["config"] = {"metrics-port": 9999, "metrics-path": "/metricspath"}
    base_state["relations"].append(
        testing.Relation(
            endpoint="metrics-endpoint",
            interface="prometheus_scrape",
        )
    )
    state = testing.State(**base_state)
    context = testing.Context(charm_type=GoCharm)

    out = context.run(context.on.config_changed(), state)

    metrics_endpoint_relations = out.get_relations("metrics-endpoint")
    assert len(metrics_endpoint_relations) == 1

    relation_data_unit = metrics_endpoint_relations[0].local_unit_data
    assert relation_data_unit["prometheus_scrape_unit_address"]
    assert relation_data_unit["prometheus_scrape_unit_name"] == "go-k8s/0"

    scrape_jobs = metrics_endpoint_relations[0].local_app_data["scrape_jobs"]
    assert "/metricspath" in scrape_jobs
    assert "*:9999" in scrape_jobs
