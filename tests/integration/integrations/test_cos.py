#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms COS integration."""
import logging
import time

# caused by pytest fixtures
# pylint: disable=too-many-arguments
import jubilant
import pytest
import requests
from ops import JujuVersion

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture",
    [
        ("expressjs_app"),
        ("go_app"),
        ("fastapi_app"),
    ],
)
@pytest.mark.skip_juju_version("3.4")
def test_prometheus_integration_noble(
    request: pytest.FixtureRequest, app_fixture: str, juju: jubilant.Juju, prometheus_app: App
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with prometheus charm.
    assert: prometheus metrics endpoint for prometheus is active and prometheus has active scrape
        targets.
    """
    prometheus_integration(request, app_fixture, juju, prometheus_app)


@pytest.mark.parametrize(
    "app_fixture",
    [
        ("flask_app"),
        ("django_app"),
    ],
)
def test_prometheus_integration(
    request: pytest.FixtureRequest, app_fixture: str, juju: jubilant.Juju, prometheus_app: App
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with prometheus charm.
    assert: prometheus metrics endpoint for prometheus is active and prometheus has active scrape
        targets.
    """

    prometheus_integration(request, app_fixture, juju, prometheus_app)


def prometheus_integration(
    request: pytest.FixtureRequest, app_fixture: str, juju: jubilant.Juju, prometheus_app: App
):
    app = request.getfixturevalue(app_fixture)
    juju.integrate(app.name, prometheus_app.name)
    juju.wait(lambda status: status.apps[app.name].is_active)
    juju.wait(lambda status: status.apps[prometheus_app.name].is_active)

    status = juju.status()
    assert status.apps[prometheus_app.name].units[prometheus_app.name + "/0"].is_active
    for unit in status.apps[prometheus_app.name].units.values():
        query_targets = requests.get(
            f"http://{unit.address}:9090/api/v1/targets", timeout=10
        ).json()
        assert len(query_targets["data"]["activeTargets"])


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("expressjs_app", 8080),
        ("go_app", 8080),
        ("fastapi_app", 8080),
    ],
)
@pytest.mark.skip_juju_version("3.4")
def test_loki_integration_noble(
    request: pytest.FixtureRequest,
    app_fixture: str,
    port: int,
    juju: jubilant.Juju,
    loki_app: App,
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with loki charm.
    assert: loki joins relation successfully, logs are being output to container and to files for
        loki to scrape.
    """
    loki_integration(request, app_fixture, port, juju, loki_app)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
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
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with loki charm.
    assert: loki joins relation successfully, logs are being output to container and to files for
        loki to scrape.
    """
    loki_integration(request, app_fixture, port, juju, loki_app)


def loki_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    port: int,
    juju: jubilant.Juju,
    loki_app: App,
):
    app = request.getfixturevalue(app_fixture)

    juju.integrate(app.name, loki_app.name)

    juju.wait(lambda status: status.apps[app.name].is_active)
    juju.wait(lambda status: status.apps[loki_app.name].is_active)
    status = juju.status()

    app_ip = status.apps[app.name].units[f"{app.name}/0"].address
    # populate the access log
    for _ in range(120):
        requests.get(f"http://{app_ip}:{port}", timeout=10)
        time.sleep(1)
    loki_ip = status.apps[loki_app.name].units[f"{loki_app.name}/0"].address
    log_query = requests.get(
        f"http://{loki_ip}:3100/loki/api/v1/query_range",
        timeout=10,
        params={"query": f'{{juju_application="{app.name}"}}'},
    ).json()
    result = log_query["data"]["result"]
    assert result
    log = result[-1]
    logging.info("retrieve sample application log: %s", log)
    assert app.name in log["stream"]["juju_application"]
    status = juju.status()
    current_version = JujuVersion(status.model.version)
    min_version = JujuVersion("3.4.0")
    if current_version < min_version:
        assert "filename" in log["stream"]
    else:
        assert "filename" not in log["stream"]


@pytest.mark.parametrize(
    "app_fixture, dashboard_name",
    [
        ("expressjs_app", "ExpressJS Operator"),
        ("go_app", "Go Operator"),
    ],
)
@pytest.mark.skip_juju_version("3.4")
def test_grafana_integration_noble(
    request: pytest.FixtureRequest,
    app_fixture: str,
    dashboard_name: str,
    juju: jubilant.Juju,
    cos_apps: dict[str:App],
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with grafana charm.
    assert: grafana 12-Factor dashboard can be found.
    """
    grafana_integration(request, app_fixture, dashboard_name, juju, cos_apps)


@pytest.mark.parametrize(
    "app_fixture, dashboard_name",
    [
        ("flask_app", "Flask Operator"),
        ("django_app", "Django Operator"),
    ],
)
def test_grafana_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    dashboard_name: str,
    juju: jubilant.Juju,
    cos_apps: dict[str:App],
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with grafana charm.
    assert: grafana 12-Factor dashboard can be found.
    """
    grafana_integration(request, app_fixture, dashboard_name, juju, cos_apps)


def grafana_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    dashboard_name: str,
    juju: jubilant.Juju,
    cos_apps: dict[str:App],
):
    app = request.getfixturevalue(app_fixture)

    juju.integrate(
        f"{cos_apps['prometheus_app'].name}:grafana-source",
        f"{cos_apps['grafana_app'].name}:grafana-source",
    )
    juju.integrate(
        f"{cos_apps['loki_app'].name}:grafana-source",
        f"{cos_apps['grafana_app'].name}:grafana-source",
    )
    juju.integrate(app.name, cos_apps["grafana_app"].name)

    juju.wait(lambda status: status.apps[app.name].is_active)
    juju.wait(lambda status: status.apps[cos_apps["grafana_app"].name].is_active)
    status = juju.status()
    task = juju.run(f"{cos_apps['grafana_app'].name}/0", "get-admin-password")
    password = task.results["admin-password"]
    grafana_ip = (
        status.apps[cos_apps["grafana_app"].name]
        .units[f"{cos_apps['grafana_app'].name}/0"]
        .address
    )
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
        params={"query": dashboard_name},
    ).json()
    assert len(dashboards)
