# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go charm unit tests."""

import pytest
from ops import testing


@pytest.mark.parametrize(
    "config, env",
    [
        pytest.param(
            {},
            {
                "PORT": "8080",
                "APP_BASE_URL": "http://go-k8s.test-model:8080",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "APP_SECRET_KEY": "test",
                "APP_OIDC_REDIRECT_PATH": "/auth/openid-connect/callback",
                "APP_OIDC_SCOPES": "openid profile email",
            },
            id="default",
        ),
        pytest.param(
            {
                "app-secret-key": "foobar",
            },
            {
                "PORT": "8080",
                "APP_BASE_URL": "http://go-k8s.test-model:8080",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "APP_SECRET_KEY": "foobar",
                "APP_OIDC_REDIRECT_PATH": "/auth/openid-connect/callback",
                "APP_OIDC_SCOPES": "openid profile email",
            },
            id="custom config",
        ),
    ],
)
def test_go_config(go_context, base_state, config: dict, env: dict) -> None:
    """
    arrange: none
    act: start the go charm and set go-app container to be ready.
    assert: go charm should submit the correct go pebble layer to pebble.
    """
    base_state["config"] = config
    state = testing.State(**base_state)
    out = go_context.run(go_context.on.config_changed(), state)

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


def test_metrics_config(go_context, base_state) -> None:
    """
    arrange: Charm with a metrics-endpoint integration
    act: Start the charm with a config-changed event.
    assert: The correct port and path for scraping should be in the relation data.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="metrics-endpoint",
            interface="prometheus_scrape",
        )
    )
    state = testing.State(**base_state)

    out = go_context.run(go_context.on.config_changed(), state)

    metrics_endpoint_relations = out.get_relations("metrics-endpoint")
    assert len(metrics_endpoint_relations) == 1

    relation_data_unit = metrics_endpoint_relations[0].local_unit_data
    assert relation_data_unit["prometheus_scrape_unit_address"]
    assert relation_data_unit["prometheus_scrape_unit_name"] == "go-k8s/0"

    scrape_jobs = metrics_endpoint_relations[0].local_app_data["scrape_jobs"]
    assert "/metrics" in scrape_jobs
    assert "*:8080" in scrape_jobs
