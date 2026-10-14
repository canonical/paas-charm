# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Rabbitmq Integration."""

import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


def _relation_exists(status: jubilant.Status, app_name: str, related_app_name: str) -> bool:
    """Check whether the application is related to RabbitMQ."""
    return any(
        relation.related_app == related_app_name
        for relation in status.apps[app_name].relations.get("rabbitmq", [])
    )


@pytest.mark.parametrize(
    "app_fixture, port, rabbitmq_app_fixture",
    [
        ("flask_app", 8000, "rabbitmq_k8s_app"),
        ("spring_boot_app", 8080, "rabbitmq_k8s_app"),
        ("go_app", 8080, "rabbitmq_k8s_app"),
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
            lambda status: _relation_exists(status, app.name, rabbitmq_app.name)
            and jubilant.all_active(status, app.name),
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
    rabbitmq_server_ha_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: The app and rabbitmq deployed
    act: Integrate the app with rabbitmq
    assert: Assert that RabbitMQ works correctly
    """
    juju.integrate(go_app.name, rabbitmq_server_ha_app.name)
    juju.wait(
        lambda status: _relation_exists(status, go_app.name, rabbitmq_server_ha_app.name)
        and jubilant.all_active(status, go_app.name),
        timeout=(10 * 60),
        delay=30,
    )
    status = juju.status()
    unit_ip = status.apps[go_app.name].units[go_app.name + "/0"].address

    response = session_with_retry.post(f"http://{unit_ip}:8080/rabbitmq/send_ha?unit=1", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" == response.text

    response = session_with_retry.get(
        f"http://{unit_ip}:8080/rabbitmq/receive_ha?unit=1", timeout=5
    )
    assert response.status_code == 200
    assert "SUCCESS" == response.text
