# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

import pytest
from ops import testing

POSTGRESQL_PASSWORD = "test-password"
POSTGRESQL_ENVIRONMENT = {
    "POSTGRESQL_DB_CONNECT_STRING": (
        f"postgresql://test-username:{POSTGRESQL_PASSWORD}@test-postgresql:5432/test-database"
    ),
    "POSTGRESQL_DB_FRAGMENT": "",
    "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
    "POSTGRESQL_DB_NAME": "test-database",
    "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
    "POSTGRESQL_DB_PARAMS": "",
    "POSTGRESQL_DB_PASSWORD": POSTGRESQL_PASSWORD,
    "POSTGRESQL_DB_PATH": "/test-database",
    "POSTGRESQL_DB_PORT": "5432",
    "POSTGRESQL_DB_QUERY": "",
    "POSTGRESQL_DB_SCHEME": "postgresql",
    "POSTGRESQL_DB_USERNAME": "test-username",
}


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
                "APP_BASE_URL": "http://expressjs-k8s.test-model:8080",
                "APP_SECRET_KEY": "test",
                "APP_OIDC_REDIRECT_PATH": "/callback",
                "APP_OIDC_SCOPES": "openid profile email",
                **POSTGRESQL_ENVIRONMENT,
            },
            id="minimal environment",
        ),
        pytest.param(
            {"JUJU_CHARM_HTTP_PROXY": "http://proxy.test"},
            {"app-secret-key": "notfoobar"},
            {
                "PORT": "8080",
                "METRICS_PORT": "9464",
                "METRICS_PATH": "/metrics",
                "NODE_ENV": "production",
                "APP_BASE_URL": "http://expressjs-k8s.test-model:8080",
                "APP_SECRET_KEY": "notfoobar",
                "HTTP_PROXY": "http://proxy.test",
                "http_proxy": "http://proxy.test",
                "APP_OIDC_REDIRECT_PATH": "/callback",
                "APP_OIDC_SCOPES": "openid profile email",
                **POSTGRESQL_ENVIRONMENT,
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
    expressjs_context,
) -> None:
    """
    arrange: set juju charm generic app with distinct combinations of configuration.
    act: generate a expressjs environment.
    assert: environment generated should contain proper proxy environment variables.
    """
    for set_env_name, set_env_value in set_env.items():
        monkeypatch.setenv(set_env_name, set_env_value)

    state = testing.State(**{**base_state, "config": config})
    out = expressjs_context.run(expressjs_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    service = out.get_container("app").plan.services["expressjs"]
    assert service.environment == expected
