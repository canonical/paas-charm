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
        prometheus_unit_ip = (
            status.apps[prometheus_app.name].units[prometheus_app.name + "/0"].address
        )
        app_unit_ip = status.apps[app.name].units[app.name + "/0"].address
        query_targets = http.get(
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
    assert: prometheus scrapes both framework default job and custom job from paas-config.yaml,
        and custom labels are present on the custom job.
    """
    try:
        juju.integrate(flask_app.name, prometheus_app.name)
        juju.wait(
            lambda status: jubilant.all_active(status, flask_app.name, prometheus_app.name),
            delay=10,
        )

        status = juju.status()
        prometheus_unit_ip = (
            status.apps[prometheus_app.name].units[prometheus_app.name + "/0"].address
        )
        app_unit_ip = status.apps[flask_app.name].units[flask_app.name + "/0"].address

        # Query Prometheus for active scrape targets
        query_targets = http.get(
            f"http://{prometheus_unit_ip}:9090/api/v1/targets", timeout=10
        ).json()
        active_targets = query_targets["data"]["activeTargets"]

        # Track which targets we found
        found_framework_job = False
        found_custom_job = False

        for active_target in active_targets:
            scrape_url = active_target["scrapeUrl"]
            labels = active_target.get("labels", {})
            job_name = labels.get("job", "")

            # Both jobs scrape port 9102/metrics, so we distinguish by job name and labels
            if "9102" in scrape_url and "/metrics" in scrape_url and app_unit_ip in scrape_url:
                # Verify target is accessible
                response = http.get(scrape_url, timeout=10)
                response.raise_for_status()

                # Check if this is the custom job from paas-config.yaml
                # Custom job should have: job_name="flask-app-custom", labels: app=flask, env=example
                if labels.get("custom") == "true":
                    assert (
                        labels.get("app") == "flask"
                    ), f"Expected label app=flask on custom job, got: {labels}"
                    assert (
                        labels.get("env") == "example"
                    ), f"Expected label env=example on custom job, got: {labels}"
                    assert (
                        job_name == "flask-app-custom"
                    ), f"Expected job_name=flask-app-custom, got: {job_name}"
                    found_custom_job = True
                    logger.info(
                        f"Found custom job from paas-config.yaml: {scrape_url}, "
                        f"job={job_name}, labels={labels}"
                    )
                else:
                    # This should be the framework default job
                    found_framework_job = True
                    logger.info(f"Found framework default job: {scrape_url}, job={job_name}")

        # Assert both jobs were found
        assert (
            found_framework_job
        ), f"Framework default job not found. Active targets: {active_targets}"
        assert (
            found_custom_job
        ), f"Custom job from paas-config.yaml not found. Active targets: {active_targets}"

    finally:
        juju.remove_relation(flask_app.name, prometheus_app.name)
