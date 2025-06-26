#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms Loki integration."""

import logging
import time

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("spring_boot_app", 8080),
        ("expressjs_app", 8080),
        ("go_app", 8080),
        ("fastapi_app", 8080),
        ("flask_app", 8000),
        ("django_app", 8000),
    ],
)
def test_loki_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    port: int,
    juju: jubilant.Juju,
    loki_app: App,
    http: requests.Session,
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with loki charm.
    assert: loki joins relation successfully, logs are being output to container and to files for
        loki to scrape.
    """
    app = request.getfixturevalue(app_fixture)

    juju.integrate(app.name, loki_app.name)

    juju.wait(lambda status: jubilant.all_active(status, app.name, loki_app.name))
    status = juju.status()

    app_ip = status.apps[app.name].units[f"{app.name}/0"].address
    # populate the access log
    for _ in range(120):
        http.get(f"http://{app_ip}:{port}", timeout=10)
        time.sleep(1)
    loki_ip = status.apps[loki_app.name].units[f"{loki_app.name}/0"].address
    log_query = http.get(
        f"http://{loki_ip}:3100/loki/api/v1/query_range",
        timeout=10,
        params={"query": f'{{juju_application="{app.name}"}}'},
    ).json()
    result = log_query["data"]["result"]
    assert result
    log = result[-1]
    logging.info("retrieve sample application log: %s", log)
    assert app.name in log["stream"]["juju_application"]
    assert "filename" not in log["stream"]
