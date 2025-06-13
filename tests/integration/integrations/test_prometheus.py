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
    "app_fixture,metrics_port,metrics_path",
    [
        ("expressjs_app", 8080, "/metrics"),
        ("go_app", 8081, "/metrics"),
        ("fastapi_app", 8080, "/metrics"),
        ("flask_app", 9102, "/metrics"),
        ("django_app", 9102, "/metrics"),
    ],
)
def test_prometheus_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    metrics_port: int,
    metrics_path: str,
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
    try:
        juju.integrate(app.name, prometheus_app.name)
        juju.wait(
            lambda status: jubilant.all_active(status, app.name, prometheus_app.name), delay=5
        )

        status = juju.status()
        prometheus_unit_ip = (
            status.apps[prometheus_app.name].units[prometheus_app.name + "/0"].address
        )
        app_unit_ip = status.apps[app.name].units[app.name + "/0"].address
        query_targets = requests.get(
            f"http://{prometheus_unit_ip}:9090/api/v1/targets", timeout=10
        ).json()
        active_targets = query_targets["data"]["activeTargets"]
        assert len(active_targets)
        for active_target in active_targets:
            scrape_url = active_target["scrapeUrl"]
            if (
                str(metrics_port) in scrape_url
                and metrics_path in scrape_url
                and app_unit_ip in scrape_url
            ):
                # scrape the url directly to see if it works
                response = requests.get(scrape_url, timeout=10)
                response.raise_for_status()
                break
        else:
            assert (
                False
            ), f"Application not scraped in port {metrics_port}. Scraped targets: {active_targets}"

    finally:
        juju.remove_relation(app.name, prometheus_app.name)
