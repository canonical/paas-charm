# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms Prometheus integration."""

import json
import logging

import jubilant
import pytest
import requests

from paas_charm.utils import build_k8s_unit_fqdn
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
    session_with_retry: requests.Session,
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

        prometheus_unit_ip, active_targets = get_prometheus_targets(
            juju, prometheus_app, session_with_retry
        )

        assert len(active_targets)
        for active_target in active_targets:
            scrape_url = active_target["scrapeUrl"]
            if (
                str(metrics_port) in scrape_url
                and metrics_path in scrape_url
                and app_unit_ip in scrape_url
            ):
                # scrape the url directly to see if it works
                response = session_with_retry.get(scrape_url, timeout=10)
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
    session_with_retry: requests.Session,
):
    """
    arrange: flask charm with paas-config.yaml containing custom scrape_configs, scaled to 2 units.
    act: establish relation with prometheus charm.
    assert: prometheus scrapes framework default jobs (port 9102 on 2 units), custom jobs
        (port 8081 on 2 units using wildcard), and scheduler-only job (port 8082 on unit 0 only
        using @scheduler placeholder). Verify custom labels and @scheduler resolves to unit 0 FQDN.
    """
    try:
        juju.add_unit(flask_app.name)
        juju.wait(lambda status: status.apps[flask_app.name].is_active)

        juju.integrate(flask_app.name, prometheus_app.name)
        juju.wait(
            lambda status: jubilant.all_active(status, flask_app.name, prometheus_app.name),
            delay=10,
        )

        status = juju.status()
        model_name = juju.model
        prometheus_unit_ip, active_targets = get_prometheus_targets(
            juju, prometheus_app, session_with_retry
        )

        framework_targets = [t for t in active_targets if ":9102" in t["scrapeUrl"]]
        custom_targets = [t for t in active_targets if ":8081" in t["scrapeUrl"]]
        scheduler_targets = [t for t in active_targets if ":8082" in t["scrapeUrl"]]

        assert len(framework_targets) == 2, (
            f"Expected 2 framework default jobs on port 9102 (wildcard expanded for 2 units), "
            f"found {len(framework_targets)}. All targets: {active_targets}"
        )

        assert len(custom_targets) == 2, (
            f"Expected 2 custom jobs on port 8081 (wildcard '*:8081' expanded for 2 units), "
            f"found {len(custom_targets)}. All targets: {active_targets}"
        )

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

        assert len(scheduler_targets) == 1, (
            f"Expected exactly 1 scheduler target on port 8082 (@scheduler:8082 targets only unit 0), "
            f"found {len(scheduler_targets)}. This proves @scheduler doesn't expand like wildcard. "
            f"All targets: {active_targets}"
        )

        scheduler_job = scheduler_targets[0]
        expected_fqdn = build_k8s_unit_fqdn(flask_app.name, "0", model_name)
        assert expected_fqdn in scheduler_job["scrapeUrl"], (
            f"Expected scheduler target to use unit 0 FQDN '{expected_fqdn}', "
            f"got: {scheduler_job['scrapeUrl']}"
        )

        assert "flask-scheduler-metrics" in scheduler_job["labels"]["job"], (
            f"Expected job_name='flask-scheduler-metrics', "
            f"got: {scheduler_job['labels']['job']}"
        )
        assert scheduler_job["labels"]["role"] == "scheduler", (
            f"Expected label role=scheduler on scheduler job, " f"got: {scheduler_job['labels']}"
        )

    finally:
        juju.remove_relation(flask_app.name, prometheus_app.name)


def get_prometheus_targets(
    juju: jubilant.Juju,
    prometheus_app: App,
    session_with_retry: requests.Session,
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
    query_targets = session_with_retry.get(
        f"http://{prometheus_unit_ip}:9090/api/v1/targets", timeout=10
    ).json()
    return prometheus_unit_ip, query_targets["data"]["activeTargets"]
