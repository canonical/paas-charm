#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Django charm."""
import asyncio
import logging
import time
import typing
from datetime import datetime

import aiohttp
import pytest
import requests
from juju.application import Application
from juju.model import Model
from juju.utils import block_until
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("django_async_app")
async def test_async_workers(
    ops_test: OpsTest,
    model: Model,
    django_async_app: Application,
    get_unit_ips,
):
    """
    arrange: Django is deployed with async enabled rock. Change gunicorn worker class.
    act: Do 15 requests that would take 2 seconds each.
    assert: All 15 requests should be served in under 3 seconds.
    """
    await django_async_app.set_config({"webserver-worker-class": "gevent"})
    await model.wait_for_idle(apps=[django_async_app.name], status="active", timeout=60)

    # the django unit is not important. Take the first one
    django_unit_ip = (await get_unit_ips(django_async_app.name))[0]

    async def _fetch_page(session):
        params = {"duration": 2}
        async with session.get(f"http://{django_unit_ip}:8000/sleep", params=params) as response:
            return await response.text()

    start_time = datetime.now()
    async with aiohttp.ClientSession() as session:
        pages = [_fetch_page(session) for _ in range(15)]
        await asyncio.gather(*pages)
        assert (
            datetime.now() - start_time
        ).seconds < 3, "Async workers for Django are not working!"
