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

WORKLOAD_PORT = 8080


@pytest.mark.parametrize(
    "app_fixture",
    [
        "go_valkey_app",
    ],
)
def test_valkey_integration(
    juju: jubilant.Juju,
    app_fixture: str,
    request: pytest.FixtureRequest,
    valkey_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: build and deploy the paas charm with valkey.
    act: deploy valkey and relate it to the charm, then write and read a key.
    assert: the charm should be able to write to and read from valkey.
    """
    app = request.getfixturevalue(app_fixture)

    juju.integrate(app.name, f"{valkey_app.name}:valkey")
    juju.wait(
        lambda status: jubilant.all_active(status, app.name, valkey_app.name), timeout=60 * 30
    )

    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address

    # Verify valkey environment variables are set
    response = session_with_retry.get(f"http://{unit_ip}:{WORKLOAD_PORT}/valkey", timeout=5)
    assert response.status_code == 200
    env_data = response.json()
    assert env_data.get("VALKEY_DB_CONNECT_STRING"), "VALKEY_DB_CONNECT_STRING not set"
    assert env_data.get("VALKEY_PASSWORD"), "VALKEY_PASSWORD not set"
    assert env_data.get("VALKEY_USERNAME"), "VALKEY_USERNAME not set"

    # Verify write/read operations work
    test_key = "integration-test-key"
    test_value = "integration-test-value"

    write_response = session_with_retry.get(
        f"http://{unit_ip}:{WORKLOAD_PORT}/write/{test_key}/{test_value}", timeout=5
    )
    assert write_response.status_code == 200
    write_data = write_response.json()
    assert write_data["status"] == "ok"

    read_response = session_with_retry.get(
        f"http://{unit_ip}:{WORKLOAD_PORT}/read/{test_key}", timeout=5
    )
    assert read_response.status_code == 200
    read_data = read_response.json()
    assert read_data["key"] == test_key
    assert read_data["value"] == test_value
