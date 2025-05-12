#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm COS integration."""
import asyncio
import logging
import typing

import juju.model
import requests
from juju.application import Application

# caused by pytest fixtures
# pylint: disable=too-many-arguments


async def test_prometheus_integration(
    model: juju.model.Model,
    prometheus_app_name: str,
    flask_app: Application,
    prometheus_app,  # pylint: disable=unused-argument
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: after Flask charm has been deployed.
    act: establish relations established with prometheus charm.
    assert: prometheus metrics endpoint for prometheus is active and prometheus has active scrape
        targets.
    """
    await model.add_relation(prometheus_app_name, flask_app.name)
    await model.wait_for_idle(apps=[flask_app.name, prometheus_app_name], status="active")

    for unit_ip in await get_unit_ips(prometheus_app_name):
        query_targets = requests.get(f"http://{unit_ip}:9090/api/v1/targets", timeout=10).json()
        assert len(query_targets["data"]["activeTargets"])


async def test_loki_integration(
    model: juju.model.Model,
    loki_app_name: str,
    flask_app: Application,
    loki_app,  # pylint: disable=unused-argument
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: after Flask charm has been deployed.
    act: establish relations established with loki charm.
    assert: loki joins relation successfully, logs are being output to container and to files for
        loki to scrape.
    """
    await model.add_relation(loki_app_name, flask_app.name)

    await model.wait_for_idle(
        apps=[flask_app.name, loki_app_name], status="active", idle_period=60
    )
    flask_ip = (await get_unit_ips(flask_app.name))[0]
    # populate the access log
    for _ in range(120):
        requests.get(f"http://{flask_ip}:8000", timeout=10)
        await asyncio.sleep(1)
    loki_ip = (await get_unit_ips(loki_app_name))[0]
    log_query = requests.get(
        f"http://{loki_ip}:3100/loki/api/v1/query_range",
        timeout=10,
        params={"query": f'{{juju_application="{flask_app.name}"}}'},
    ).json()
    result = log_query["data"]["result"]
    assert result
    log = result[-1]
    logging.info("retrieve sample application log: %s", log)
    assert any("python-requests" in line[1] for line in log["values"])
    assert "filename" not in log["stream"]


async def test_grafana_integration(
    model: juju.model.Model,
    flask_app: Application,
    prometheus_app_name: str,
    loki_app_name: str,
    grafana_app_name: str,
    cos_apps,  # pylint: disable=unused-argument
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: after Flask charm has been deployed.
    act: establish relations established with grafana charm.
    assert: grafana Flask dashboard can be found.
    """
    await model.relate(
        f"{prometheus_app_name}:grafana-source", f"{grafana_app_name}:grafana-source"
    )
    await model.relate(f"{loki_app_name}:grafana-source", f"{grafana_app_name}:grafana-source")
    await model.relate(flask_app.name, grafana_app_name)

    await model.wait_for_idle(
        apps=[flask_app.name, prometheus_app_name, loki_app_name, grafana_app_name],
        status="active",
        idle_period=60,
    )

    action = await model.applications[grafana_app_name].units[0].run_action("get-admin-password")
    await action.wait()
    password = action.results["admin-password"]
    grafana_ip = (await get_unit_ips(grafana_app_name))[0]
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
        params={"query": "Flask Operator"},
    ).json()
    assert len(dashboards)
