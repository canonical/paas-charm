# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Go charm."""

import logging
import typing

import jubilant
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)
WORKLOAD_PORT = 8080


def test_go_is_up(
    go_app: App,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the go charm.
    act: send a request to the go application managed by the go charm.
    assert: the go application should return a correct response.
    """
    for unit_ip in get_unit_ips(go_app.name):
        response = requests.get(f"http://{unit_ip}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


def test_user_defined_config(
    juju: jubilant.Juju,
    go_app: App,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the go charm. Set the config user-defined-config to a new value.
    act: call the endpoint to get the value of the env variable related to the config.
    assert: the value of the env variable and the config should match.
    """
    juju.config(go_app.name, {"user-defined-config": "newvalue"})
    juju.wait(
        lambda status: jubilant.all_active(status, [go_app.name]),
    )

    for unit_ip in get_unit_ips(go_app.name):
        response = requests.get(
            f"http://{unit_ip}:{WORKLOAD_PORT}/env/user-defined-config", timeout=5
        )
        assert response.status_code == 200
        assert "newvalue" in response.text


def test_migration(
    go_app: App,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the go charm with postgresql integration.
    act: send a request to an endpoint that uses the table created by the migration script.
    assert: the go application should return a correct response.
    """
    for unit_ip in get_unit_ips(go_app.name):
        response = requests.get(
            f"http://{unit_ip}:{WORKLOAD_PORT}/postgresql/migratestatus", timeout=5
        )
        assert response.status_code == 200
        assert "SUCCESS" in response.text


def test_prometheus_integration(
    juju: jubilant.Juju,
    go_app: App,
    prometheus_app: App,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: after Go charm has been deployed.
    act: establish relations established with prometheus charm.
    assert: prometheus metrics endpoint for prometheus is active and prometheus has active scrape
        targets.
    """
    juju.integrate(go_app.name, prometheus_app.name)
    juju.wait(
        lambda status: jubilant.all_active(status, [go_app.name, prometheus_app.name]),
    )

    config = juju.config(go_app.name)
    juju.config(go_app.name, {"metrics-path": str(config["metrics-port"] + 1)})

    juju.wait(
        lambda status: jubilant.all_active(status, [go_app.name, prometheus_app.name]),
    )
    config = juju.config(go_app.name)

    for unit_ip in get_unit_ips(prometheus_app.name):
        query_targets = requests.get(f"http://{unit_ip}:9090/api/v1/targets", timeout=10).json()
        active_targets = query_targets["data"]["activeTargets"]
        assert len(active_targets)
        for active_target in active_targets:
            scrape_url = active_target["scrapeUrl"]
            metrics_path = config["metrics-path"]
            metrics_port = str(config["metrics-port"])
            if metrics_path in scrape_url and metrics_port in scrape_url:
                break
        else:
            logger.error("Application not scraped. Scraped targets: %s", active_targets)
            assert False, "Scrape Target not configured correctly"
