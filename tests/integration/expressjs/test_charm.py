#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""ExpressJS integration tests."""

import logging

import jubilant
import pytest
import requests

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8080


@pytest.mark.skip_juju_version("3.4")
def test_expressjs_is_up(request: pytest.FixtureRequest, juju: jubilant.Juju):
    """Check that the charm is active."""
    expressjs_app = request.getfixturevalue("expressjs_app")
    status = juju.status()
    assert status.apps[expressjs_app.name].units[expressjs_app.name + "/0"].is_active
    for unit in status.apps[expressjs_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


@pytest.mark.skip_juju_version("3.4")
def test_user_defined_config(request: pytest.FixtureRequest, juju: jubilant.Juju):
    """
    arrange: build and deploy the ExpressJS charm. Set the config user-defined-config to a new value.
    act: call the endpoint to get the value of the env variable related to the config.
    assert: the value of the env variable and the config should match.
    """
    expressjs_app = request.getfixturevalue("expressjs_app")
    juju.config(expressjs_app.name, {"user-defined-config": "newvalue"})
    juju.wait(lambda status: status.apps[expressjs_app.name].is_active)
    juju.wait(lambda status: status.apps["postgresql-k8s"].is_active)

    status = juju.status()
    for unit in status.apps[expressjs_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/env/user-defined-config", timeout=5
        )
        assert response.status_code == 200
        assert "newvalue" in response.text


@pytest.mark.skip_juju_version("3.4")
def test_migration(request: pytest.FixtureRequest, juju: jubilant.Juju):
    """
    arrange: build and deploy the ExpressJS charm with postgresql integration.
    act: send a request to an endpoint that checks the table created by the migration script.
        Then try to add same user twice.
    assert: the ExpressJS application should add the user only once.
    """
    expressjs_app = request.getfixturevalue("expressjs_app")
    status = juju.status()
    for unit in status.apps[expressjs_app.name].units.values():
        response = requests.get(f"http://{unit.address}:{WORKLOAD_PORT}/table/users", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" in response.text
        user_creation_request = {"username": "foo", "password": "bar"}
        response = requests.post(
            f"http://{unit.address}:8080/users", json=user_creation_request, timeout=5
        )
        assert response.status_code == 201
        response = requests.post(
            f"http://{unit.address}:8080/users", json=user_creation_request, timeout=5
        )
        assert response.status_code == 400
