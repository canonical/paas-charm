#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Springboot integration tests."""

import logging

import jubilant
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8080


def test_springboot_is_up(spring_boot_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the Springboot charm.
    act: call the endpoint.
    assert: the charm should respond with 200 OK.
    """
    status = juju.status()
    assert status.apps[spring_boot_app.name].units[spring_boot_app.name + "/0"].is_active
    for unit in status.apps[spring_boot_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text
