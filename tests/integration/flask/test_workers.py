# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import asyncio
import logging
import time

import pytest
import requests
from juju.application import Application
from juju.model import Model
from juju.utils import block_until
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "num_units",
    [1, 3],
)
@pytest.mark.usefixtures("integrate_redis_k8s_flask")
async def test_workers_and_scheduler_services(
    ops_test: OpsTest, model: Model, flask_app: Application, get_unit_ips, num_units: int
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
    await flask_app.scale(num_units)
    await model.wait_for_idle(apps=[flask_app.name], status="active")

    # the flask unit is not important. Take the first one
    flask_unit_ip = (await get_unit_ips(flask_app.name))[0]

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

    # clean the current celery stats
    response = requests.get(f"http://{flask_unit_ip}:8000/redis/clear_celery_stats", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" == response.text

    # enough time for all the schedulers to send messages
    time.sleep(10)
    try:
        await block_until(
            lambda: check_correct_celery_stats(num_schedulers=1, num_workers=num_units),
            timeout=60,
            wait_period=1,
        )
    except asyncio.TimeoutError:
        assert False, "Failed to get 2 workers and 1 scheduler"


@pytest.mark.parametrize(
    "worker_class, expected_result",
    [
        ("eventlet", "blocked"),
        ("gevent", "active"),
        ("sync", "active"),
    ],
)
@pytest.mark.usefixtures("flask_async_app")
async def test_async_workers(
    ops_test: OpsTest,
    model: Model,
    flask_async_app: Application,
    get_unit_ips,
    worker_class: str,
    expected_result: bool,
):
    """
    arrange: Flask is deployed with async enabled rock.
    act: Change gunicorn worker class.
    assert: Charm should only let the class to be 'sync' or 'gevent'.
    If it is something other than these, then the unit should be blocked.
    """
    await flask_async_app.set_config({"webserver-worker-class": worker_class})
    await model.wait_for_idle(apps=[flask_async_app.name], status=expected_result, timeout=60)


@pytest.mark.parametrize(
    "worker_class, expected_result",
    [
        ("gevent", "blocked"),
        ("eventlet", "blocked"),
        ("sync", "active"),
    ],
)
@pytest.mark.usefixtures("flask_app")
async def test_async_workers_fail(
    ops_test: OpsTest,
    model: Model,
    flask_app: Application,
    get_unit_ips,
    worker_class: str,
    expected_result: str,
):
    """
    arrange: Flask is deployed with async not enabled rock.
    act: Change gunicorn worker class.
    assert: Charm should only let the class to be 'sync'.
    If it is 'gevent' or something else, then the unit should be blocked.
    """
    await flask_app.set_config({"webserver-worker-class": worker_class})
    await model.wait_for_idle(apps=[flask_app.name], status=expected_result, timeout=60)
