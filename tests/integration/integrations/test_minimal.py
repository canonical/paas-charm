# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask minimal charm."""

import logging

import jubilant
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


def test_flask_minimal(
    juju: jubilant.Juju,
    flask_minimal_app: App,
):
    """
    arrange: Build and deploy the charm with minimal integrations.
    act: Send a request to the web application.
    assert: The request succeeds.
    """
    status = juju.status()
    unit_ip = status.apps[flask_minimal_app.name].units[flask_minimal_app.name + "/0"].address
    response = requests.get(f"http://{unit_ip}:8000/", timeout=5)
    assert "Hello" in response.text
    assert response.status_code == 200
