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
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=5,
    connect=5,
    read=5,
    other=5,
    backoff_factor=5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "POST", "GET", "OPTIONS"],
    raise_on_status=False,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("http://", adapter)


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
        response = http.get(f"http://{unit.address}:{WORKLOAD_PORT}/hello-world", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


def test_migration(spring_boot_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the Springboot charm with postgresql integration.
    act: send a request to an endpoint that checks the table created by the migration script.
        Then try to add same user twice.
    assert: the Springboot application should add the user only once.
    """
    status = juju.status()
    for unit in status.apps[spring_boot_app.name].units.values():
        response = http.get(f"http://{unit.address}:{WORKLOAD_PORT}/table/users", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" in response.text
        user_creation_request = {"name": "foo", "password": "bar"}
        response = requests.post(
            f"http://{unit.address}:{WORKLOAD_PORT}/users", json=user_creation_request, timeout=5
        )
        assert response.status_code == 201
        response = requests.post(
            f"http://{unit.address}:{WORKLOAD_PORT}/users", json=user_creation_request, timeout=5
        )
        assert response.status_code == 400
