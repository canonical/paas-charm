#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for ExpressJS charm COS integration."""
import logging
import time

# caused by pytest fixtures
# pylint: disable=too-many-arguments
import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8080


@pytest.mark.skip_juju_version("3.4")  # Tempo only supports Juju>=3.4
def test_prometheus_integration(
    expressjs_app: App,
    juju: jubilant.Juju,
    prometheus_app_name: str,
    prometheus_app,  # pylint: disable=unused-argument
):
    """
    arrange: after Flask charm has been deployed.
    act: establish relations established with prometheus charm.
    assert: prometheus metrics endpoint for prometheus is active and prometheus has active scrape
        targets.
    """
    juju.integrate(expressjs_app.name, prometheus_app_name)
    juju.wait(jubilant.all_active)

    status = juju.status()
    assert status.apps[prometheus_app_name].units[prometheus_app_name + "/0"].is_active
    for unit in status.apps[prometheus_app_name].units.values():
        query_targets = requests.get(
            f"http://{unit.address}:9090/api/v1/targets", timeout=10
        ).json()
        assert len(query_targets["data"]["activeTargets"])


@pytest.mark.skip_juju_version("3.4")  # Tempo only supports Juju>=3.4
def test_loki_integration(
    expressjs_app: App,
    juju: jubilant.Juju,
    loki_app_name: str,
    loki_app,  # pylint: disable=unused-argument
):
    """
    arrange: after Flask charm has been deployed.
    act: establish relations established with loki charm.
    assert: loki joins relation successfully, logs are being output to container and to files for
        loki to scrape.
    """

    juju.integrate(expressjs_app.name, loki_app_name)
    juju.wait(jubilant.all_active)

    status = juju.status()

    expressjs_ip = status.apps[expressjs_app.name].units[f"{expressjs_app.name}/0"].address
    # populate the access log
    for _ in range(120):
        requests.get(f"http://{expressjs_ip}:8080", timeout=10)
        time.sleep(1)
    loki_ip = status.apps[loki_app_name].units[f"{loki_app_name}/0"].address
    log_query = requests.get(
        f"http://{loki_ip}:3100/loki/api/v1/query_range",
        timeout=10,
        params={"query": f'{{juju_application="{expressjs_app.name}"}}'},
    ).json()
    result = log_query["data"]["result"]
    assert result
    log = result[-1]
    logging.info("retrieve sample application log: %s", log)
    assert expressjs_app.name in log["stream"]["juju_application"]
    assert "filename" not in log["stream"]


@pytest.mark.skip_juju_version("3.4")  # Tempo only supports Juju>=3.4
def test_grafana_integration(
    expressjs_app: App,
    juju: jubilant.Juju,
    prometheus_app_name: str,
    loki_app_name: str,
    grafana_app_name: str,
    cos_apps,  # pylint: disable=unused-argument
):
    """
    arrange: after Flask charm has been deployed.
    act: establish relations established with grafana charm.
    assert: grafana Flask dashboard can be found.
    """

    juju.integrate(f"{prometheus_app_name}:grafana-source", f"{grafana_app_name}:grafana-source")
    juju.integrate(f"{loki_app_name}:grafana-source", f"{grafana_app_name}:grafana-source")
    juju.integrate(expressjs_app.name, grafana_app_name)
    juju.wait(jubilant.all_active)

    status = juju.status()
    task = juju.run(f"{grafana_app_name}/0", "get-admin-password")
    password = task.results["admin-password"]
    grafana_ip = status.apps[grafana_app_name].units[f"{grafana_app_name}/0"].address
    sess = requests.session()
    sess.post(
        f"http://{grafana_ip}:3000/login",
        json={
            "user": "admin",
            "password": password,
        },
    ).raise_for_status()
    datasources = sess.get(f"http://{grafana_ip}:3000/api/datasources", timeout=10).json()
    datasource_types = set(datasource["type"] for datasource in datasources)
    assert "loki" in datasource_types
    assert "prometheus" in datasource_types
    dashboards = sess.get(
        f"http://{grafana_ip}:3000/api/search",
        timeout=10,
        params={"query": "ExpressJS Operator"},
    ).json()
    assert len(dashboards)
