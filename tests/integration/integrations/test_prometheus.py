# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms Prometheus integration."""

import json
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

        prometheus_unit_ip, active_targets = _get_prometheus_targets(
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
        prometheus_unit_ip, active_targets = _get_prometheus_targets(
            juju, prometheus_app, session_with_retry
        )

        framework_targets = [t for t in active_targets if ":9102" in t["scrapeUrl"]]
        custom_targets = [t for t in active_targets if ":8081" in t["scrapeUrl"]]
        scheduler_targets = [t for t in active_targets if ":8082" in t["scrapeUrl"]]

        _verify_targets_for_both_units(framework_targets, flask_app.name, 9102, "framework")

        _verify_targets_for_both_units(custom_targets, flask_app.name, 8081, "custom")
        _verify_labels(custom_targets[0], {"app": "flask", "env": "example"})
        assert "flask-app-custom" in custom_targets[0]["labels"]["job"]

        scheduler_job = _verify_single_target_for_unit(
            scheduler_targets, flask_app.name, 0, 8082, "scheduler"
        )
        _verify_labels(scheduler_job, {"role": "scheduler"})
        assert "flask-scheduler-metrics" in scheduler_job["labels"]["job"]

    finally:
        juju.remove_unit(flask_app.name, num_units=1)
        juju.remove_relation(flask_app.name, prometheus_app.name)


def _get_prometheus_targets(
    juju: jubilant.Juju,
    prometheus_app: App,
    session_with_retry: requests.Session,
) -> tuple[str, list[dict]]:
    """Get active scrape targets from Prometheus."""
    status = juju.status()
    prometheus_unit_ip = status.apps[prometheus_app.name].units[prometheus_app.name + "/0"].address
    query_targets = session_with_retry.get(
        f"http://{prometheus_unit_ip}:9090/api/v1/targets", timeout=10
    ).json()
    return prometheus_unit_ip, query_targets["data"]["activeTargets"]


def _verify_targets_for_both_units(
    targets: list[dict], app_name: str, port: int, target_type: str
) -> None:
    """Verify targets list contains exactly 2 targets for unit 0 and unit 1."""
    urls = [t["scrapeUrl"] for t in targets]
    assert (
        len(targets) == 2
    ), f"Expected 2 {target_type} targets on port {port}, found {len(targets)}. URLs: {urls}"
    for unit_num in [0, 1]:
        assert any(
            f"{app_name}-{unit_num}" in url for url in urls
        ), f"Expected {target_type} target for unit {unit_num}, got: {urls}"


def _verify_labels(target: dict, expected_labels: dict[str, str]) -> None:
    """Verify target has expected labels."""
    for key, expected_value in expected_labels.items():
        actual_value = target["labels"].get(key)
        assert (
            actual_value == expected_value
        ), f"Expected {key}={expected_value}, got {key}={actual_value}"


def _verify_single_target_for_unit(
    targets: list[dict], app_name: str, unit: int, port: int, target_type: str
) -> dict:
    """Verify exactly one target exists for specific unit."""
    assert (
        len(targets) == 1
    ), f"Expected exactly 1 {target_type} target on port {port}, found {len(targets)}"
    target = targets[0]
    assert (
        f"{app_name}-{unit}" in target["scrapeUrl"]
    ), f"Expected {target_type} for {app_name}-{unit}, got: {target['scrapeUrl']}"
    return target
