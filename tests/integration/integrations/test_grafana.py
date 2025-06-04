#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms Grafana integration."""

import logging

import jubilant
import pytest
import requests

from tests.integration.helpers import (
    check_grafana_dashboards_patiently,
    check_grafana_datasource_types_patiently,
)
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

    juju.integrate(app.name, cos_apps["grafana_app"].name)

    juju.wait(lambda status: jubilant.all_active(status, app.name, cos_apps["grafana_app"].name))
    status = juju.status()
    task = juju.run(f"{cos_apps['grafana_app'].name}/0", "get-admin-password")
    password = task.results["admin-password"]
    grafana_ip = (
        status.apps[cos_apps["grafana_app"].name]
        .units[f"{cos_apps['grafana_app'].name}/0"]
        .address
    )
    with requests.session() as sess:
        sess.post(
            f"http://{grafana_ip}:3000/login",
            json={
                "user": "admin",
                "password": password,
            },
        ).raise_for_status()
        check_grafana_datasource_types_patiently(sess, grafana_ip, ["prometheus", "loki"])
        check_grafana_dashboards_patiently(sess, grafana_ip, dashboard_name)
