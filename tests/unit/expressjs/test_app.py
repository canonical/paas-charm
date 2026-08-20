# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

import pytest
from ops import testing

from examples.expressjs.charm.src.charm import ExpressJSCharm


@pytest.mark.parametrize(
    "set_env, config, expected",
    [
        pytest.param(
            {},
            {},
            {
                "PORT": "8080",
                "METRICS_PORT": "9464",
                "METRICS_PATH": "/metrics",
                "NODE_ENV": "production",
            },
            id="minimal environment",
        ),
        pytest.param(
            {"JUJU_CHARM_HTTP_PROXY": "http://proxy.test"},
            {
                "app-secret-key": "notfoobar",
            },
            {
                "PORT": "8080",
                "METRICS_PORT": "9464",
                "METRICS_PATH": "/metrics",
                "NODE_ENV": "production",
                "APP_SECRET_KEY": "notfoobar",
                "HTTP_PROXY": "http://proxy.test",
                "http_proxy": "http://proxy.test",
            },
            id="all configurable values set",
        ),
    ],
)
def test_expressjs_environment_vars(
    monkeypatch,
    set_env,
    config,
    expected,
    base_state,
):
    """
    arrange: set juju charm generic app with distinct combinations of configuration.
    act: generate a expressjs environment.
    assert: environment generated should contain proper proxy environment variables.
    """
    for set_env_name, set_env_value in set_env.items():
        monkeypatch.setenv(set_env_name, set_env_value)

    base_state["config"] = config
    state = testing.State(**base_state)
    context = testing.Context(charm_type=ExpressJSCharm)

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    env = out.get_container("app").plan.services["expressjs"].environment
    assert {key: env[key] for key in expected} == expected
