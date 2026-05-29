#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Valkey database integration."""

import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port, endpoint",
    [
        ("flask_app", 8000, "valkey/status"),
    ],
)
def test_with_valkey(
    juju: jubilant.Juju,
    app_fixture: str,
    port,
    endpoint: str,
    request: pytest.FixtureRequest,
    valkey_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: build and deploy the paas charm.
    act: deploy the valkey database and relate it to the charm.
    assert: requesting the charm should return a correct response.
    """
    app = request.getfixturevalue(app_fixture)

    juju.integrate(app.name, valkey_app.name)
    juju.wait(
        lambda status: jubilant.all_active(status, app.name, valkey_app.name), timeout=60 * 30
    )

    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address
    response = session_with_retry.get(f"http://{unit_ip}:{port}/{endpoint}", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" in response.text, f"Response: {response.text}"
