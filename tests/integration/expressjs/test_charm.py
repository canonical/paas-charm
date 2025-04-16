#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""ExpressJS integration tests."""

import logging

import jubilant
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8080


def test_expressjs_is_up(expressjs_app: App, juju: jubilant.Juju):
    """Check that the charm is active.
    Assume that the charm has already been built and is running.
    """
    status = juju.status()
    assert status.apps[expressjs_app.name].units[expressjs_app.name + "/0"].is_active
    for unit in status.apps[expressjs_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


def test_user_defined_config(expressjs_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the fastapi charm. Set the config user-defined-config to a new value.
    act: call the endpoint to get the value of the env variable related to the config.
    assert: the value of the env variable and the config should match.
    """
    juju.config(expressjs_app.name, {"user-defined-config": "newvalue"})
    juju.wait(jubilant.all_active)

    status = juju.status()
    for unit in status.apps[expressjs_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/env/user-defined-config", timeout=5
        )
        assert response.status_code == 200
        assert "newvalue" in response.text


def test_migration(expressjs_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the fastapi charm with postgresql integration.
    act: send a request to an endpoint that checks the table created by the micration script.
    assert: the fastapi application should return a correct response.
    """
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
