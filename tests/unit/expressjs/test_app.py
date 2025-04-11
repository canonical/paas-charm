# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""ExpressJS charm unit tests for the generic app module."""

import pathlib
import unittest

import pytest

from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState, IntegrationsState
from paas_charm.expressjs.charm import ExpressJSConfig


@pytest.mark.parametrize(
    "set_env, user_defined_config, framework_config, integrations, expected",
    [
        pytest.param(
            {},
            {},
            {},
            None,
            {
                "PORT": "8080",
                "NODE_ENV": "production",
                "APP_SECRET_KEY": "foobar",
                "APP_OTHERCONFIG": "othervalue",
                "APP_BASE_URL": "https://paas.example.com",
            },
        ),
        pytest.param(
            {"JUJU_CHARM_HTTP_PROXY": "http://proxy.test"},
            {"extra-config", "extravalue"},
            {"metrics-port": "9000", "metrics-path": "/m", "app-secret-key": "notfoobar"},
            IntegrationsState(
                redis_uri="redis://10.1.88.132:6379",
                rabbitmq_uri="amqp://expressjs-app:test-password@rabbitmq.example.com/%2f",
            ),
            {
                "PORT": "8080",
                "NODE_ENV": "production",
                "METRICS_PATH": "/m",
                "METRICS_PORT": "9000",
                "APP_SECRET_KEY": "notfoobar",
                "APP_OTHERCONFIG": "othervalue",
                "APP_BASE_URL": "https://paas.example.com",
                "HTTP_PROXY": "http://proxy.test",
                "http_proxy": "http://proxy.test",
                "REDIS_DB_CONNECT_STRING": "redis://10.1.88.132:6379",
                "REDIS_DB_FRAGMENT": "",
                "REDIS_DB_HOSTNAME": "10.1.88.132",
                "REDIS_DB_NETLOC": "10.1.88.132:6379",
                "REDIS_DB_PARAMS": "",
                "REDIS_DB_PATH": "",
                "REDIS_DB_PORT": "6379",
                "REDIS_DB_QUERY": "",
                "REDIS_DB_SCHEME": "redis",
                "RABBITMQ_HOSTNAME": "rabbitmq.example.com",
                "RABBITMQ_PASSWORD": "test-password",
                "RABBITMQ_USERNAME": "expressjs-app",
                "RABBITMQ_VHOST": "/",
                "RABBITMQ_CONNECT_STRING": "amqp://expressjs-app:test-password@rabbitmq.example.com/%2f",
                "RABBITMQ_FRAGMENT": "",
                "RABBITMQ_NETLOC": "expressjs-app:test-password@rabbitmq.example.com",
                "RABBITMQ_PARAMS": "",
                "RABBITMQ_PATH": "/%2f",
                "RABBITMQ_QUERY": "",
                "RABBITMQ_SCHEME": "amqp",
            },
        ),
    ],
)
def test_expressjs_environment_vars(
    monkeypatch, set_env, user_defined_config, framework_config, integrations, expected
):
    """
    arrange: set juju charm generic app with distinct combinations of configuration.
    act: generate a expressjs environment.
    assert: environment generated should contain proper proxy environment variables.
    """
    for set_env_name, set_env_value in set_env.items():
        monkeypatch.setenv(set_env_name, set_env_value)

    framework_name = "expressjs"
    framework_config = ExpressJSConfig.model_validate(framework_config)
    base_dir = pathlib.Path("/app")
    workload_config = WorkloadConfig(
        framework=framework_name,
        container_name="app",
        port=framework_config.port,
        base_dir=base_dir,
        app_dir=base_dir,
        state_dir=base_dir / "state",
        service_name=framework_name,
        log_files=[],
        metrics_target=f"*:{framework_config.metrics_port}",
        metrics_path=framework_config.metrics_path,
        unit_name="expressjs/0",
    )

    charm_state = CharmState(
        framework="expressjs",
        secret_key="foobar",
        is_secret_storage_ready=True,
        framework_config=framework_config.dict(exclude_none=True),
        base_url="https://paas.example.com",
        user_defined_config={"otherconfig": "othervalue"},
        integrations=integrations,
    )

    app = App(
        container=unittest.mock.MagicMock(),
        charm_state=charm_state,
        workload_config=workload_config,
        database_migration=unittest.mock.MagicMock(),
        framework_config_prefix="",
    )
    env = app.gen_environment()
    assert env == expected
