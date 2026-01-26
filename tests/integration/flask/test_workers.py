# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import concurrent.futures
import logging
import time
from datetime import datetime

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="redis_k8s_app")
def redis_k8s_app_fixture(juju: jubilant.Juju):
    """Deploy Redis k8s charm."""
    redis_app_name = "redis-k8s"
    if not juju.status().apps.get(redis_app_name):
        juju.deploy(redis_app_name, channel="edge")
    juju.wait(lambda status: status.apps[redis_app_name].is_active)
    return App(redis_app_name)


@pytest.fixture
def integrate_redis_k8s_flask(juju: jubilant.Juju, flask_app: App, redis_k8s_app: App):
    """Integrate redis_k8s with flask apps."""
    try:
        juju.integrate(flask_app.name, redis_k8s_app.name)
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    juju.wait(lambda status: status.apps[redis_k8s_app.name].is_active, timeout=10 * 60)
    yield
    juju.remove_relation(flask_app.name, f"{redis_k8s_app.name}:redis")
    juju.wait(lambda status: status.apps[flask_app.name].is_active, timeout=10 * 60)


@pytest.mark.parametrize(
    "num_units",
    [1, 3],
)
@pytest.mark.usefixtures("integrate_redis_k8s_flask")
def test_workers_and_scheduler_services(
    juju: jubilant.Juju,
    flask_app: App,
    http: requests.Session,
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
    juju.scale(flask_app.name, num_units)
    juju.wait(lambda status: status.apps[flask_app.name].is_active)

    # the flask unit is not important. Take the first one
    status = juju.status()
    flask_unit_ip = list(status.apps[flask_app.name].units.values())[0].address

    def check_correct_celery_stats(num_schedulers, num_workers):
        """Check that the expected number of workers and schedulers is right."""
        response = http.get(f"http://{flask_unit_ip}:8000/redis/celery_stats", timeout=5)
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
    response = http.get(f"http://{flask_unit_ip}:8000/redis/clear_celery_stats", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" == response.text

    # enough time for all the schedulers to send messages
    time.sleep(10)

    # Wait up to 60 seconds for correct stats
    deadline = time.time() + 60
    while time.time() < deadline:
        if check_correct_celery_stats(num_schedulers=1, num_workers=num_units):
            return
        time.sleep(1)

    # Final check
    assert check_correct_celery_stats(
        num_schedulers=1, num_workers=num_units
    ), f"Failed to get {num_units} workers and 1 scheduler"


@pytest.mark.usefixtures("flask_async_app")
def test_async_workers(
    juju: jubilant.Juju,
    flask_async_app: App,
    http: requests.Session,
):
    """
    arrange: Flask is deployed with async enabled rock. Change gunicorn worker class.
    act: Do 15 requests that would take 2 seconds each.
    assert: All 15 requests should be served in under 3 seconds.
    """
    juju.config(flask_async_app.name, {"webserver-worker-class": "gevent"})
    juju.wait(lambda status: status.apps[flask_async_app.name].is_active, timeout=60)

    # the flask unit is not important. Take the first one
    status = juju.status()
    flask_unit_ip = list(status.apps[flask_async_app.name].units.values())[0].address

    # Use threading to make concurrent requests
    def fetch_page():
        params = {"duration": 2}
        response = http.get(f"http://{flask_unit_ip}:8000/sleep", params=params, timeout=5)
        return response.text

    start_time = datetime.now()
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(fetch_page) for _ in range(15)]
        concurrent.futures.wait(futures)

    elapsed_seconds = (datetime.now() - start_time).total_seconds()
    assert elapsed_seconds < 3, f"Async workers for Flask are not working! Took {elapsed_seconds}s"
