#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Django charm."""
import logging
import time
from datetime import datetime

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("django_async_app")
def test_async_workers(
    juju: jubilant.Juju,
    django_async_app: App,
):
    """
    arrange: Django is deployed with async enabled rock. Change gunicorn worker class.
    act: Do 15 requests that would take 2 seconds each.
    assert: All 15 requests should be served in under 3 seconds.
    """
    juju.config(django_async_app.name, {"webserver-worker-class": "gevent"})
    juju.wait(lambda status: jubilant.all_active(status, django_async_app.name), timeout=60)

    # the django unit is not important. Take the first one
    status = juju.status()
    django_unit = list(status.apps[django_async_app.name].units.values())[0]
    django_unit_ip = django_unit.address

    # Use concurrent requests with requests library
    import concurrent.futures

    def fetch_page():
        params = {"duration": 2}
        response = requests.get(f"http://{django_unit_ip}:8000/sleep", params=params, timeout=10)
        return response.text

    start_time = datetime.now()
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(fetch_page) for _ in range(15)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    elapsed_time = (datetime.now() - start_time).seconds
    assert elapsed_time < 3, "Async workers for Django are not working!"
