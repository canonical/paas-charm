# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go charm unit tests for the generic app module."""

import pathlib
from unittest.mock import MagicMock

import pytest

from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState, IntegrationsState
from paas_charm.go.charm import GoConfig
from paas_charm.rabbitmq import PaaSRabbitMQRelationData
from paas_charm.redis import PaaSRedisRelationData


@pytest.mark.parametrize(
    "set_env, user_defined_config, framework_config, integrations, expected",
    [
        pytest.param(
            {},
            {"otherconfig": "othervalue"},
            {},
            None,
            {
                "APP_PORT": "8080",
                "APP_SECRET_KEY": "foobar",
                "APP_OTHERCONFIG": "othervalue",
                "APP_BASE_URL": "https://paas.example.com",
            },
        ),
        pytest.param(
            {"JUJU_CHARM_HTTP_PROXY": "http://proxy.test"},
            {"extra-config": "extravalue"},
            {"metrics-port": "9000", "metrics-path": "/m", "app-secret-key": "notfoobar"},
            IntegrationsState(
                redis=PaaSRedisRelationData(url="redis://10.1.88.132:6379"),
                rabbitmq=PaaSRabbitMQRelationData(
                    vhost="/",
                    port=5672,
                    hostname="rabbitmq.example.com",
                    username="go-app",
                    password="test-password",
                    amqp_uri="amqp://go-app:test-password@rabbitmq.example.com/%2f",
                ),
            ),
            {
                "APP_PORT": "8080",
                "APP_METRICS_PATH": "/m",
                "APP_METRICS_PORT": "9000",
                "APP_SECRET_KEY": "notfoobar",
                "APP_EXTRA-CONFIG": "extravalue",
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
                "RABBITMQ_USERNAME": "go-app",
                "RABBITMQ_VHOST": "/",
                "RABBITMQ_CONNECT_STRING": "amqp://go-app:test-password@rabbitmq.example.com:5672/%2F",
                "RABBITMQ_FRAGMENT": "",
                "RABBITMQ_NETLOC": "go-app:test-password@rabbitmq.example.com:5672",
                "RABBITMQ_PARAMS": "",
                "RABBITMQ_PATH": "/%2F",
                "RABBITMQ_PORT": "5672",
                "RABBITMQ_QUERY": "",
                "RABBITMQ_SCHEME": "amqp",
            },
        ),
    ],
)
def test_go_environment_vars(
    monkeypatch, set_env, user_defined_config, framework_config, integrations, expected
):
    """
    arrange: set juju charm generic app with distinct combinations of configuration.
    act: generate a go environment.
    assert: environment generated should contain proper proxy environment variables.
    """
    for set_env_name, set_env_value in set_env.items():
        monkeypatch.setenv(set_env_name, set_env_value)

    framework_name = "go"
    framework_config = GoConfig.model_validate(framework_config)
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
        unit_name="go/0",
    )

    charm_state = CharmState(
        framework="go",
        secret_key="foobar",
        is_secret_storage_ready=True,
        framework_config=framework_config.dict(exclude_none=True),
        base_url="https://paas.example.com",
        user_defined_config=user_defined_config,
        integrations=integrations,
    )

    app = App(
        container=MagicMock(),
        charm_state=charm_state,
        workload_config=workload_config,
        database_migration=MagicMock(),
    )
    env = app.gen_environment()
    assert env == expected
