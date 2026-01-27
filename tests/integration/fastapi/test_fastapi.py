# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for FastAPI charm."""

import logging

import jubilant
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)
WORKLOAD_PORT = 8080


def test_fastapi_is_up(fastapi_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the fastapi charm.
    act: send a request to the fastapi application managed by the fastapi charm.
    assert: the fastapi application should return a correct response.
    """
    status = juju.status()
    for unit in status.apps[fastapi_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


def test_user_defined_config(fastapi_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the fastapi charm. Set the config user-defined-config to a new value.
    act: call the endpoint to get the value of the env variable related to the config.
    assert: the value of the env variable and the config should match.
    """
    juju.config(fastapi_app.name, {"user-defined-config": "newvalue"})
    juju.wait(lambda status: jubilant.all_active(status, fastapi_app.name, "postgresql-k8s"))

    status = juju.status()
    for unit in status.apps[fastapi_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/env/user-defined-config", timeout=5
        )
        assert response.status_code == 200
        assert "newvalue" in response.text


def test_migration(fastapi_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the fastapi charm with postgresql integration.
    act: send a request to an endpoint that checks the table created by the micration script.
    assert: the fastapi application should return a correct response.
    """
    status = juju.status()
    for unit in status.apps[fastapi_app.name].units.values():
        response = requests.get(f"http://{unit.address}:{WORKLOAD_PORT}/table/users", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" in response.text
