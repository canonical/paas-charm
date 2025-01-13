# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for FastAPI charm."""

import logging
import typing

import pytest
import requests
from juju.application import Application
from juju.model import Model

logger = logging.getLogger(__name__)
WORKLOAD_PORT = 8080


async def test_fastapi_is_up(
    fastapi_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the fastapi charm.
    act: send a request to the fastapi application managed by the fastapi charm.
    assert: the fastapi application should return a correct response.
    """
    for unit_ip in await get_unit_ips(fastapi_app.name):
        response = requests.get(f"http://{unit_ip}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


async def test_user_defined_config(
    model: Model,
    fastapi_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the fastapi charm. Set the config user-defined-config to a new value.
    act: call the endpoint to get the value of the env variable related to the config.
    assert: the value of the env variable and the config should match.
    """
    await fastapi_app.set_config({"user-defined-config": "newvalue"})
    await model.wait_for_idle(apps=[fastapi_app.name], status="active")

    for unit_ip in await get_unit_ips(fastapi_app.name):
        response = requests.get(
            f"http://{unit_ip}:{WORKLOAD_PORT}/env/user-defined-config", timeout=5
        )
        assert response.status_code == 200
        assert "newvalue" in response.text


async def test_migration(
    fastapi_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the fastapi charm with postgresql integration.
    act: send a request to an endpoint that checks the table created by the micration script.
    assert: the fastapi application should return a correct response.
    """
    for unit_ip in await get_unit_ips(fastapi_app.name):
        response = requests.get(f"http://{unit_ip}:{WORKLOAD_PORT}/table/users", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" in response.text
