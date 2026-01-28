# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import logging
import time
from datetime import datetime

import aiohttp
import asyncio
import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "num_units",
    [1, 3],
)
@pytest.mark.usefixtures("integrate_redis_k8s_flask_jubilant")
def test_workers_and_scheduler_services(
    juju: jubilant.Juju,
    flask_app_with_configs: App,
    num_units: int,
):
    """
    arrange: Flask and redis deployed and integrated.
    act: Scale the app to the desired number of units.
    assert: There should be only one scheduler and as many workers as units. That will
            be checked because the scheduler is constantly sending tasks with its hostname
            to the workers, and the workers will put its own hostname and the schedulers
            hostname in Redis sets. Those sets are checked through the Flask app,
            that queries Redis.
    """
    juju.cli("scale-application", flask_app_with_configs.name, str(num_units))
    juju.wait(lambda status: jubilant.all_active(status, flask_app_with_configs.name), timeout=10 * 60)

    # Get the first flask unit IP
    status = juju.status()
    flask_unit_ip = list(status.apps[flask_app_with_configs.name].units.values())[0].address

    def check_correct_celery_stats(num_schedulers, num_workers):
        """Check that the expected number of workers and schedulers is right."""
        response = requests.get(f"http://{flask_unit_ip}:8000/redis/celery_stats", timeout=5)
        assert response.status_code == 200
        data = response.json()
        logger.info(
            "check_correct_celery_stats. Expected schedulers: %d, expected workers %d. Result %s",
            num_schedulers,
            num_workers,
            data,
        )
        return len(data["workers"]) == num_workers and len(data["schedulers"]) == num_schedulers

    # Clean the current celery stats
    response = requests.get(f"http://{flask_unit_ip}:8000/redis/clear_celery_stats", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" == response.text

    # Enough time for all the schedulers to send messages
    time.sleep(10)
    
    # Poll for correct stats
    for _ in range(60):
        if check_correct_celery_stats(num_schedulers=1, num_workers=num_units):
            return
        time.sleep(1)
    
    assert False, "Failed to get correct number of workers and schedulers"


def test_async_workers(
    juju: jubilant.Juju,
    flask_async_app: App,
):
    """
    arrange: Flask is deployed with async enabled rock. Change gunicorn worker class.
    act: Do 15 requests that would take 2 seconds each.
    assert: All 15 requests should be served in under 3 seconds.
    """
    juju.config(flask_async_app.name, {"webserver-worker-class": "gevent"})
    juju.wait(lambda status: jubilant.all_active(status, flask_async_app.name), timeout=10 * 60)

    # Get the flask unit IP
    status = juju.status()
    flask_unit_ip = list(status.apps[flask_async_app.name].units.values())[0].address

    async def _fetch_page(session):
        params = {"duration": 2}
        async with session.get(f"http://{flask_unit_ip}:8000/sleep", params=params) as response:
            return await response.text()

    async def run_async_test():
        start_time = datetime.now()
        async with aiohttp.ClientSession() as session:
            pages = [_fetch_page(session) for _ in range(15)]
            await asyncio.gather(*pages)
            assert (
                datetime.now() - start_time
            ).seconds < 3, "Async workers for Flask are not working!"
    
    # Run the async test
    asyncio.run(run_async_test())
