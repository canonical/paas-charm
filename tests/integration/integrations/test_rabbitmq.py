# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Rabbitmq Integration."""
import logging

import jubilant
import pytest
import requests

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port, rabbitmq_app_fixture",
    [
        ("flask_app", 8000, "rabbitmq_server_app"),
        ("flask_app", 8000, "rabbitmq_k8s_app"),
    ],
)
def test_rabbitmq_server_integration(
    juju: jubilant.Juju,
    app_fixture: str,
    rabbitmq_app_fixture: str,
    port: int,
    request: pytest.FixtureRequest,
):
    """
    arrange: Flask and rabbitmq deployed
    act: Integrate flask with rabbitmq
    assert: Assert that RabbitMQ works correctly
    """
    app = request.getfixturevalue(app_fixture)
    rabbitmq_app = request.getfixturevalue(rabbitmq_app_fixture)

    try:
        juju.integrate(app.name, rabbitmq_app.name)
        juju.wait(lambda status: jubilant.all_active(status, app.name), timeout=6 * 60, delay=10)
        status = juju.status()
        unit_ip = status.apps[app.name].units[app.name + "/0"].address

        response = requests.get(f"http://{unit_ip}:{port}/rabbitmq/send", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text

        response = requests.get(f"http://{unit_ip}:{port}/rabbitmq/receive", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text
    finally:
        juju.remove_relation(app.name, rabbitmq_app.name)
