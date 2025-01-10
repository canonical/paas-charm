# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import asyncio
import logging
import time

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

    async def _fetch_page(session):
        params = {"duration": 2}
        async with session.get(f"http://{flask_unit_ip}:8000", params=params) as response:
            return await response.text()

    async with aiohttp.ClientSession() as session:
        page = _fetch_page(session)
        await asyncio.gather([page])

    print("--------------------------")
    print(f"{flask_tracing_app.name}-app")
    print("--------------------------")
    # verify workload traces are ingested into Tempo
    assert await get_traces_patiently(
        await get_application_ip(ops_test, tempo_app.name),
        service_name=f"{flask_tracing_app.name}-app",
        tls=False,
    )
