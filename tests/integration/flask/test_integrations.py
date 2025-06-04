# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm integrations, like Rabbitmq."""
import logging

import pytest
import requests
from juju.application import Application

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("rabbitmq_server_integration")
async def test_rabbitmq_server_integration(
    flask_app: Application,
    get_unit_ips,
):
    """
    arrange: Flask and rabbitmq-server deployed
    act: Integrate flask with rabbitmq-server
    assert: Assert that RabbitMQ works correctly
    """
    await assert_rabbitmq_integration_correct(flask_app, get_unit_ips)


@pytest.mark.usefixtures("rabbitmq_k8s_integration")
async def test_rabbitmq_k8s_integration(
    flask_app: Application,
    get_unit_ips,
):
    """
    arrange: Flask and rabbitmq-k8s deployed
    act: Integrate flask with rabbitmq-k8s
    assert: Assert that RabbitMQ works correctly

    """
    await assert_rabbitmq_integration_correct(flask_app, get_unit_ips)


async def assert_rabbitmq_integration_correct(flask_app: Application, get_unit_ips):
    """Assert that rabbitmq works correctly sending and receiving a message."""
    for unit_ip in await get_unit_ips(flask_app.name):
        response = requests.get(f"http://{unit_ip}:8000/rabbitmq/send", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text

        response = requests.get(f"http://{unit_ip}:8000/rabbitmq/receive", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text
