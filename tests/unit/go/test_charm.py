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
            },
            {
                "APP_PORT": "8080",
                "APP_BASE_URL": "http://go-k8s.test-model:8080",
                "APP_METRICS_PORT": "8080",
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
