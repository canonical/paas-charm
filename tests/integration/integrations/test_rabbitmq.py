# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Rabbitmq Integration."""
import logging

import pytest
import requests
import jubilant

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("flask_app", 8000),
    ]
)
def test_rabbitmq_server_integration(
    juju: jubilant.Juju,
    app_fixture: str,
    port: int,
    request: pytest.FixtureRequest,
    # TODO this is a trick, this is really "model-lxd.rabbitmq-server"
    rabbitmq_server_app,
    lxd_controller_name,
    lxd_model_name
):
    """
    arrange: Flask and rabbitmq-server deployed
    act: Integrate flask with rabbitmq-server
    assert: Assert that RabbitMQ works correctly
    """
    rabbitmq_offer_url = f"{lxd_controller_name}:admin/{lxd_model_name}.{rabbitmq_server_app.name}"

    app = request.getfixturevalue(app_fixture)
    # TODO rabbitmq_server_app is really a url offer
    juju.integrate(app.name, rabbitmq_offer_url)

    juju.wait(lambda status: jubilant.all_active(status, app.name), delay=10)

    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address

    send_url = f"http://{unit_ip}:8000/rabbitmq/send"
    logger.info("JAVI Sending request to %s", send_url)
    response = requests.get(f"http://{unit_ip}:{port}/rabbitmq/send", timeout=5)
    logger.info("JAVI RESPONSE %s", response)
    assert response.status_code == 200
    assert "SUCCESS" == response.text

    response = requests.get(f"http://{unit_ip}:{port}/rabbitmq/receive", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" == response.text
