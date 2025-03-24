#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for non-root Charms Loki integration."""

import asyncio
import logging
import typing

import juju.client.client
import juju.model
import pytest
import requests
from juju.application import Application

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "non_root_app_fixture, port",
    [
        pytest.param("flask_non_root_app", 8000, id="Flask non-root"),
        pytest.param("django_non_root_app", 8000, id="Django non-root"),
        pytest.param("fastapi_non_root_app", 8080, id="FastAPI non-root"),
        pytest.param("go_non_root_app", 8080, id="Go non-root"),
    ],
)
@pytest.mark.skip_juju_version("3.6")  # Only Juju>=3.6 supports non-root users
async def test_non_root_loki_integration(
    model: juju.model.Model,
    loki_app_name: str,
    non_root_app_fixture: str,
    port: int,
    loki_app: Application,  # pylint: disable=unused-argument
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
    request,
):
    """
    arrange: after non-root charm has been deployed.
    act: establish relations established with loki charm.
    assert: loki joins relation successfully, logs are being output to container and to files for
        loki to scrape.
    """
    non_root_app = request.getfixturevalue(non_root_app_fixture)
    await model.add_relation(loki_app_name, non_root_app.name)

    await model.wait_for_idle(
        apps=[non_root_app.name, loki_app_name], status="active", idle_period=60
    )
    unit_ip = (await get_unit_ips(non_root_app.name))[0]
    # populate the access log
    for _ in range(120):
        requests.get(f"http://{unit_ip}:{port}", timeout=10)
        await asyncio.sleep(1)
    loki_ip = (await get_unit_ips(loki_app_name))[0]
    log_query = requests.get(
        f"http://{loki_ip}:3100/loki/api/v1/query_range",
        timeout=10,
        params={"query": f'{{juju_application="{non_root_app.name}"}}'},
    ).json()
    result = log_query["data"]["result"]
    assert result
    log = result[-1]
    logging.info("retrieve sample application log: %s", log)
    assert log["values"]  # any("python-requests" in line[1] for line in log["values"])
    if model.info.agent_version < juju.client.client.Number.from_json("3.4.0"):
        assert "filename" in log["stream"]
    else:
        assert "filename" not in log["stream"]
