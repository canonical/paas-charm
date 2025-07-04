#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for MongoDB database integration."""
import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port, endpoint",
    [
        ("flask_app", 8000, "mysql/status"),
        ("spring_boot_mysql_app", 8080, "mysql/status"),
    ],
)
def test_with_mysql(
    juju: jubilant.Juju,
    app_fixture: App,
    port,
    endpoint: str,
    request: pytest.FixtureRequest,
    mysql_app: App,
    http: requests.Session,
):
    """
    arrange: build and deploy the paas charm.
    act: deploy the MySQL database and relate it to the charm.
    assert: requesting the charm should return a correct response
    """
    app = request.getfixturevalue(app_fixture)

    juju.integrate(app.name, mysql_app.name)
    juju.wait(
        lambda status: jubilant.all_active(status, app.name, mysql_app.name), timeout=60 * 30
    )

    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address

    response = http.get(f"http://{unit_ip}:{port}/{endpoint}", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" in response.text, f"Response: {response.text}"
