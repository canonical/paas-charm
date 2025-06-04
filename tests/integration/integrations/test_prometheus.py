# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms Prometheus integration."""

import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture",
    [
        ("expressjs_app"),
        ("go_app"),
        ("fastapi_app"),
        ("flask_app"),
        ("django_app"),
    ],
)
def test_prometheus_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    juju: jubilant.Juju,
    prometheus_app: App,
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with prometheus charm.
    assert: prometheus metrics endpoint for prometheus is active and prometheus has active scrape
        targets.
    """
    app = request.getfixturevalue(app_fixture)
    juju.integrate(app.name, prometheus_app.name)
    juju.wait(lambda status: jubilant.all_active(status, app.name, prometheus_app.name))

    status = juju.status()
    assert status.apps[prometheus_app.name].units[prometheus_app.name + "/0"].is_active
    for unit in status.apps[prometheus_app.name].units.values():
        query_targets = requests.get(
            f"http://{unit.address}:9090/api/v1/targets", timeout=10
        ).json()
        assert len(query_targets["data"]["activeTargets"])
