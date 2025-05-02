#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms Grafana integration."""
import logging

# caused by pytest fixtures
# pylint: disable=too-many-arguments
import jubilant
import pytest
import requests

from tests.integration.helpers import check_grafana_datasource_types_patiently
from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, dashboard_name",
    [
        ("expressjs_app", "ExpressJS Operator"),
        ("go_app", "Go Operator"),
        ("flask_app", "Flask Operator"),
        ("django_app", "Django Operator"),
    ],
)
@pytest.mark.skip_juju_version("3.4")
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

    juju.wait(lambda status: jubilant.all_active(status, [app.name, cos_apps["grafana_app"].name]))
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
    check_grafana_datasource_types_patiently(sess,grafana_ip, ["prometheus", "loki"])
    dashboards = sess.get(
        f"http://{grafana_ip}:3000/api/search",
        timeout=10,
        params={"query": dashboard_name},
    ).json()
    assert len(dashboards)
