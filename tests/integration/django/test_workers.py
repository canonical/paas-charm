#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Django charm."""
import asyncio
import logging
import typing
from datetime import datetime

import aiohttp
import jubilant
import pytest

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("django_async_app")
async def test_async_workers(
    juju: jubilant.Juju,
    django_async_app: App,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: Django is deployed with async enabled rock. Change gunicorn worker class.
    act: Do 15 requests that would take 2 seconds each.
    assert: All 15 requests should be served in under 3 seconds.
    """
    juju.config(django_async_app.name, {"webserver-worker-class": "gevent"})
    juju.wait(
        lambda status: jubilant.all_active(status, [django_async_app.name]),
        timeout=60,
    )

    # the django unit is not important. Take the first one
    django_unit_ip = get_unit_ips(django_async_app.name)[0]

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
