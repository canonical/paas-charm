# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""S3 lib wrapper unit tests."""

from unittest.mock import MagicMock

import pytest

from paas_charm.app import RabbitMQEnvironmentMapper
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.rabbitmq import RabbitMQRelationData, RabbitMQRequires


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            RabbitMQRelationData.model_construct(
                port=5672,
                hostname="test-url.com",
                username="testusername",
                password="testpassword",
                amqp_uri="amqp://testusername:testpassword@test-url.com:5672",
            ),
            {
                "RABBITMQ_CONNECT_STRING": "amqp://testusername:testpassword@test-url.com:5672",
                "RABBITMQ_FRAGMENT": "",
                "RABBITMQ_HOSTNAME": "test-url.com",
                "RABBITMQ_NETLOC": "testusername:testpassword@test-url.com:5672",
                "RABBITMQ_PARAMS": "",
                "RABBITMQ_PASSWORD": "testpassword",
                "RABBITMQ_PATH": "",
                "RABBITMQ_PORT": "5672",
                "RABBITMQ_QUERY": "",
                "RABBITMQ_SCHEME": "amqp",
                "RABBITMQ_USERNAME": "testusername",
            },
            id="Minimum relation data",
        ),
        pytest.param(
            RabbitMQRelationData.model_construct(
                port=5672,
                hostname="test-url.com",
                username="testusername",
                password="testpassword",
                amqp_uri="amqp://testusername:testpassword@test-url.com:5672/testvhost",
                vhost="testvhost",
            ),
            {
                "RABBITMQ_CONNECT_STRING": "amqp://testusername:testpassword@test-url.com:5672/testvhost",
                "RABBITMQ_FRAGMENT": "",
                "RABBITMQ_HOSTNAME": "test-url.com",
                "RABBITMQ_NETLOC": "testusername:testpassword@test-url.com:5672",
                "RABBITMQ_PARAMS": "",
                "RABBITMQ_PASSWORD": "testpassword",
                "RABBITMQ_PATH": "/testvhost",
                "RABBITMQ_PORT": "5672",
                "RABBITMQ_QUERY": "",
                "RABBITMQ_SCHEME": "amqp",
                "RABBITMQ_USERNAME": "testusername",
                "RABBITMQ_VHOST": "testvhost",
            },
            id="All relation data",
        ),
    ],
)
def test_rabbitmq_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given S3 relation data.
    act: when generate_env method is called.
    assert: expected environment variables are generated.
    """
    assert RabbitMQEnvironmentMapper.generate_env(relation_data) == expected_env
