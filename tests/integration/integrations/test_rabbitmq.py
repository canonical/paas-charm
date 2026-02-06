# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Rabbitmq Integration."""

import logging

import jubilant
import pytest
import requests

from tests.integration.helpers import jubilant_temp_controller
from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port, rabbitmq_app_fixture",
    [
        ("flask_app", 8000, "rabbitmq_k8s_app"),
        ("spring_boot_app", 8080, "rabbitmq_k8s_app"),
        ("go_app", 8080, "rabbitmq_k8s_app"),
        ("flask_app", 8000, "rabbitmq_server_app"),
        ("go_app", 8080, "rabbitmq_server_app"),
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
    arrange: The app and rabbitmq deployed
    act: Integrate the app with rabbitmq
    assert: Assert that RabbitMQ works correctly
    """
    app = request.getfixturevalue(app_fixture)
    rabbitmq_app = request.getfixturevalue(rabbitmq_app_fixture)

    try:
        juju.integrate(app.name, rabbitmq_app.name)
        juju.wait(
            lambda status: jubilant.all_active(status, app.name),
            timeout=(10 * 60),
            delay=30,
        )
        status = juju.status()
        unit_ip = status.apps[app.name].units[app.name + "/0"].address

        response = requests.post(f"http://{unit_ip}:{port}/rabbitmq/send", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text

        response = requests.get(f"http://{unit_ip}:{port}/rabbitmq/receive", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text
    finally:
        juju.remove_relation(app.name, rabbitmq_app.name)


def test_rabbitmq_ha_integration(
    juju: jubilant.Juju,
    go_app: App,
    rabbitmq_app_fixture: str,
    request: pytest.FixtureRequest,
    lxd_controller,
    lxd_model,
):
    """
    arrange: The app and rabbitmq deployed
    act: Integrate the app with rabbitmq
    assert: Assert that RabbitMQ works correctly
    """
    rabbitmq_app = request.getfixturevalue(rabbitmq_app_fixture)

    try:
        juju.integrate(go_app.name, rabbitmq_app.name)
        juju.wait(
            lambda status: jubilant.all_active(status, go_app.name),
            timeout=(10 * 60),
            delay=30,
        )
        status = juju.status()
        unit_ip = status.apps[go_app.name].units[go_app.name + "/0"].address

        response = requests.post(f"http://{unit_ip}:8080/rabbitmq/send_ha?unit=1", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text

        response = requests.get(f"http://{unit_ip}:8080/rabbitmq/receive_ha?unit=1", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text
    finally:
        with jubilant_temp_controller(juju, lxd_controller, lxd_model):
            juju.add_unit(rabbitmq_app.name, num_units=1)
            juju.wait(
                lambda status: jubilant.all_active(status, rabbitmq_app.name),
                timeout=6 * 60,
                delay=10,
            )
        juju.remove_relation(go_app.name, rabbitmq_app.name)
