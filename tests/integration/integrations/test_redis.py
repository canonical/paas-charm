#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm database integration."""
import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port, endpoint",
    [
        ("flask_app", 8000, "redis/status"),
        ("spring_boot_app", 8080, "redis/status"),
    ],
)
def test_with_database(
    juju: jubilant.Juju,
    app_fixture: App,
    port,
    endpoint: str,
    request: pytest.FixtureRequest,
    redis_app: App,
    http: requests.Session,
):
    """
    arrange: build and deploy the paas charm.
    act: deploy the redis database and relate it to the charm.
    assert: requesting the charm should return a correct response
    """
    app = request.getfixturevalue(app_fixture)

    juju.integrate(app.name, redis_app.name)
    juju.wait(lambda status: jubilant.all_active(status, app.name, redis_app.name))

    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address
    response = http.get(f"http://{unit_ip}:{port}/{endpoint}", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" in response.text, f"Response: {response.text}"
