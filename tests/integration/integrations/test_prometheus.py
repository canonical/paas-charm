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
        ("flask_app", 9102, "/metrics"),
        ("django_app", 9102, "/metrics"),
        ("spring_boot_app", 8080, "/actuator/prometheus"),
        ("expressjs_app", 8080, "/metrics"),
        ("go_app", 8081, "/metrics"),
        ("fastapi_app", 8080, "/metrics"),
    ],
)
def test_prometheus_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    metrics_port: int,
    metrics_path: str,
    juju: jubilant.Juju,
    prometheus_app: App,
    http: requests.Session,
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
            lambda status: jubilant.all_active(status, app.name, prometheus_app.name), delay=10
        )

        status = juju.status()
        app_unit_ip = status.apps[app.name].units[app.name + "/0"].address

        prometheus_unit_ip, active_targets = get_prometheus_targets(juju, prometheus_app, http)

        assert len(active_targets)
        for active_target in active_targets:
            scrape_url = active_target["scrapeUrl"]
            if (
                str(metrics_port) in scrape_url
                and metrics_path in scrape_url
                and app_unit_ip in scrape_url
            ):
                # scrape the url directly to see if it works
                response = http.get(scrape_url, timeout=10)
                response.raise_for_status()
                break
        else:
            assert (
                False
            ), f"Application not scraped in port {metrics_port}. Scraped targets: {active_targets}"

    finally:
        juju.remove_relation(app.name, prometheus_app.name)


def test_prometheus_custom_scrape_configs(
    flask_app: App,
    prometheus_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
):
    """
    arrange: flask charm with paas-config.yaml containing custom scrape_configs.
    act: establish relation with prometheus charm.
    assert: prometheus scrapes both framework default job (port 9102) and custom job
        (port 8081) from paas-config.yaml, and custom labels are present on the custom job.
    """
    try:
        juju.integrate(flask_app.name, prometheus_app.name)
        juju.wait(
            lambda status: jubilant.all_active(status, flask_app.name, prometheus_app.name),
            delay=10,
        )

        status = juju.status()
        app_unit_ip = status.apps[flask_app.name].units[flask_app.name + "/0"].address
        prometheus_unit_ip, active_targets = get_prometheus_targets(juju, prometheus_app, http)

        # Filter targets for this app by port
        framework_targets = [
            t
            for t in active_targets
            if app_unit_ip in t["scrapeUrl"] and ":9102" in t["scrapeUrl"]
        ]
        custom_targets = [
            t
            for t in active_targets
            if app_unit_ip in t["scrapeUrl"] and ":8081" in t["scrapeUrl"]
        ]

        # Assert framework default job exists (port 9102)
        assert len(framework_targets) == 1, (
            f"Expected 1 framework default job on port 9102, found {len(framework_targets)}. "
            f"All targets: {active_targets}"
        )

        # Assert custom job from paas-config.yaml exists (port 8081)
        assert len(custom_targets) == 1, (
            f"Expected 1 custom job on port 8081 from paas-config.yaml, "
            f"found {len(custom_targets)}. All targets: {active_targets}"
        )

        # Verify custom job has correct job_name and labels
        custom_job = custom_targets[0]
        assert (
            "flask-app-custom" in custom_job["labels"]["job"]
        ), f"Expected job_name='flask-app-custom', got: {custom_job['labels']['job']}"
        assert (
            custom_job["labels"]["app"] == "flask"
        ), f"Expected label app=flask on custom job, got: {custom_job['labels']}"
        assert (
            custom_job["labels"]["env"] == "example"
        ), f"Expected label env=example on custom job, got: {custom_job['labels']}"

    finally:
        juju.remove_relation(flask_app.name, prometheus_app.name)


def get_prometheus_targets(
    juju: jubilant.Juju,
    prometheus_app: App,
    http: requests.Session,
) -> tuple[str, list[dict]]:
    """Get active scrape targets from Prometheus.

    Args:
        juju: Juju controller interface.
        prometheus_app: Prometheus application.
        http: HTTP session for making requests.

    Returns:
        Tuple of (prometheus_unit_ip, active_targets_list).
    """
    status = juju.status()
    prometheus_unit_ip = status.apps[prometheus_app.name].units[prometheus_app.name + "/0"].address
    query_targets = http.get(f"http://{prometheus_unit_ip}:9090/api/v1/targets", timeout=10).json()
    return prometheus_unit_ip, query_targets["data"]["activeTargets"]
