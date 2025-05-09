# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import asyncio
import logging

import aiohttp
import pytest
from juju.errors import JujuError
from juju.model import Model
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import get_traces_patiently

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "tracing_app_fixture, port",
    [
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
    ],
)
async def test_workload_tracing(
    ops_test: OpsTest,
    model: Model,
    tracing_app_fixture: str,
    port: int,
    request: pytest.FixtureRequest,
    get_unit_ips,
):
    """
    arrange: Deploy Tempo cluster, app to test and postgres if required.
    act: Send 5 requests to the app.
    assert: Tempo should have tracing info about the app.
    """
    try:
        tempo_app = request.getfixturevalue("tempo_app")
    except JujuError as e:
        if "application already exists" in str(e):
            logger.info(f"Tempo is already deployed  {e}")
            tempo_app = model.applications["tempo"]
        else:
            raise e
    tracing_app = request.getfixturevalue(tracing_app_fixture)

    await ops_test.model.integrate(f"{tracing_app.name}:tracing", f"{tempo_app.name}:tracing")

    await ops_test.model.wait_for_idle(
        apps=[tracing_app.name, tempo_app.name], status="active", timeout=600
    )

    unit_ip = (await get_unit_ips(tracing_app.name))[0]
    tempo_host = (await get_unit_ips(tempo_app.name))[0]

    async def _fetch_page(session):
        async with session.get(f"http://{unit_ip}:{port}") as response:
            return await response.text()

    async with aiohttp.ClientSession() as session:
        pages = [_fetch_page(session) for _ in range(5)]
        await asyncio.gather(*pages)

    # verify workload traces are ingested into Tempo
    assert await get_traces_patiently(tempo_host, tracing_app.name)
