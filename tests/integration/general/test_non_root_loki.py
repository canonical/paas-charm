#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for non-root Charms Loki integration."""

import logging
import time

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "non_root_app_fixture, port",
    [
        pytest.param("flask_non_root_app", 8000, id="Flask non-root"),
        pytest.param("django_non_root_app", 8000, id="Django non-root"),
        pytest.param("fastapi_non_root_app", 8080, id="FastAPI non-root"),
        pytest.param("go_non_root_app", 8080, id="Go non-root"),
        pytest.param("expressjs_non_root_app", 8080, id="ExpressJS non-root"),
    ],
)
def test_non_root_loki_integration(
    juju: jubilant.Juju,
    non_root_app_fixture: str,
    port: int,
    loki_app: App,
    request,
):
    """
    arrange: after non-root charm has been deployed.
    act: establish relations established with loki charm.
    assert: loki joins relation successfully, logs are being output to container and to files for
        loki to scrape.
    """
    non_root_app = request.getfixturevalue(non_root_app_fixture)
    try:
        juju.integrate(loki_app.name, non_root_app.name)
        juju.wait(
            lambda status: jubilant.all_active(status, non_root_app.name, loki_app.name), delay=10
        )
        status = juju.status()
        unit_ip = status.apps[non_root_app.name].units[non_root_app.name + "/0"].address
        # populate the access log
        for _ in range(10):
            requests.get(f"http://{unit_ip}:{port}", timeout=10)
        # Give some time for the logs to be pushed to loki.
        time.sleep(10)
        loki_ip = status.apps[loki_app.name].units[loki_app.name + "/0"].address
        log_query = requests.get(
            f"http://{loki_ip}:3100/loki/api/v1/query_range",
            timeout=10,
            params={"query": f'{{juju_application="{non_root_app.name}"}}'},
        ).json()
        # In Flask and Django, other streams exists (like the celery workers).
        # Just test that there is something.
        result = log_query["data"]["result"]
        assert result
        log = result[-1]
        logging.info("retrieve sample application log: %s", log)
        assert log["values"]
        assert "filename" not in log["stream"]
    finally:
        juju.remove_relation(loki_app.name, non_root_app.name)
