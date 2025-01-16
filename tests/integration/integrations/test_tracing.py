# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import asyncio
import json
import logging
import time

import aiohttp
import pytest
from juju.application import Application
from juju.model import Model
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import get_traces_patiently

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "tracing_app, port",
    [
        ("flask_tracing_app", 8000),
        ("django_tracing_app", 8000),
        ("fastapi_tracing_app", 8080),
        ("go_tracing_app", 8080),
    ],
    indirect["tracing_app"],
)
@pytest.mark.skip_juju_version("3.4")  # Tempo only supports Juju>=3.4
async def test_workload_tracing(
    ops_test: OpsTest,
    model: Model,
    tracing_app: Application,
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
        tempo_app = await request.getfixturevalue("tempo_app")
    except Exception as e:
        logger.info(f"Tempo is already deployed  {e}")

    idle_list = [tracing_app.name]

    if tracing_app.name != "flask-tracing-k8s":
        try:
            postgresql_app = request.getfixturevalue("postgresql_k8s")
        except Exception as e:
            logger.info(f"Postgres is already deployed   {e}")
        await model.integrate(tracing_app.name, "postgresql-k8s")
        idle_list.append("postgresql-k8s")
    await model.wait_for_idle(apps=idle_list, status="active", timeout=300)

    tempo_app_name = "tempo"

    await ops_test.model.integrate(f"{tracing_app.name}:tracing", f"{tempo_app_name}:tracing")

    await ops_test.model.wait_for_idle(
        apps=[tracing_app.name, tempo_app_name], status="active", timeout=600
    )

    unit_ip = (await get_unit_ips(tracing_app.name))[0]
    tempo_host = (await get_unit_ips(tempo_app_name))[0]

    async def _fetch_page(session):
        async with session.get(f"http://{unit_ip}:{port}") as response:
            return await response.text()

    async with aiohttp.ClientSession() as session:
        pages = [_fetch_page(session) for _ in range(5)]
        await asyncio.gather(*pages)

    # verify workload traces are ingested into Tempo
    assert await get_traces_patiently(tempo_host, tracing_app.name)
