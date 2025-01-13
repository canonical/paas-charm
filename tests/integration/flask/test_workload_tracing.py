# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import asyncio
import logging
import time
import json

import aiohttp
import pytest
from juju.application import Application
from juju.model import Model
from pytest_operator.plugin import OpsTest
logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("flask_tracing_app")
@pytest.mark.usefixtures("tempo_app")
async def test_workload_tracing(
    ops_test: OpsTest,
    model: Model,
    flask_tracing_app: Application,
    tempo_app: Application,
    get_unit_ips,
):
    """
    arrange: Flask is deployed with async enabled rock. Change gunicorn worker class.
    act: Do 15 requests that would take 2 seconds each.
    assert: All 15 requests should be served in under 3 seconds.
    """
    await ops_test.model.integrate(
        f"{flask_tracing_app.name}:tracing", f"{tempo_app.name}:tracing"
    )

    await ops_test.model.wait_for_idle(
        apps=[flask_tracing_app.name, tempo_app.name], status="active", timeout=300
    )
    # the flask unit is not important. Take the first one
    flask_unit_ip = (await get_unit_ips(flask_tracing_app.name))[0]
    tempo_host = (await get_unit_ips(tempo_app.name))[0]

    async def _fetch_page(session):
        async with session.get(f"http://{flask_unit_ip}:8000") as response:
            return await response.text()

    async def _fetch_trace(session):
        async with session.get(
            f"http://{tempo_host}:3200/api/search?tags=service.name={flask_tracing_app.name}") as response:
            text = await response.text()
            return json.loads(text)["traces"]

    async with aiohttp.ClientSession() as session:
        pages = [_fetch_page(session) for _ in range(5)]
        await asyncio.gather(*pages)

    # wait a little for traces to register
    time.sleep(5)
    # verify workload traces are ingested into Tempo
    async with aiohttp.ClientSession() as session:
        pages = [_fetch_trace(session) for _ in range(5)]
        traces = await asyncio.gather(*pages)
        assert len(traces) > 0
