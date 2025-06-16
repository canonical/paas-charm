# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Go charm."""

import logging
import typing

import requests
from juju.application import Application
from juju.model import Model
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)
WORKLOAD_PORT = 8080


async def test_go_is_up(
    go_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the go charm.
    act: send a request to the go application managed by the go charm.
    assert: the go application should return a correct response.
    """
    for unit_ip in await get_unit_ips(go_app.name):
        response = requests.get(f"http://{unit_ip}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


async def test_user_defined_config(
    model: Model,
    go_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the go charm. Set the config user-defined-config to a new value.
    act: call the endpoint to get the value of the env variable related to the config.
    assert: the value of the env variable and the config should match.
    """
    await go_app.set_config({"user-defined-config": "newvalue"})
    await model.wait_for_idle(apps=[go_app.name], status="active")

    for unit_ip in await get_unit_ips(go_app.name):
        response = requests.get(
            f"http://{unit_ip}:{WORKLOAD_PORT}/env/user-defined-config", timeout=5
        )
        assert response.status_code == 200
        assert "newvalue" in response.text


async def test_migration(
    go_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the go charm with postgresql integration.
    act: send a request to an endpoint that uses the table created by the migration script.
    assert: the go application should return a correct response.
    """
    for unit_ip in await get_unit_ips(go_app.name):
        response = requests.get(
            f"http://{unit_ip}:{WORKLOAD_PORT}/postgresql/migratestatus", timeout=5
        )
        assert response.status_code == 200
        assert "SUCCESS" in response.text


async def test_open_ports(
    ops_test: OpsTest,
    model: Model,
    go_app: Application,
    traefik_app: Application,
    get_unit_ips,
    external_hostname,
):
    """
    arrange: after Go charm has been deployed.
    act: integrate with the traefik charm with the ingress integration and change app-port configuration.
    assert: charm opened ports should change accordingly.
    """
    await model.add_relation(traefik_app.name, go_app.name)
    await model.wait_for_idle(apps=[go_app.name, traefik_app.name], status="active")
    traefik_ip = (await get_unit_ips(traefik_app.name))[0]

    juju_cmd = ["exec", "--unit", f"{go_app.name}/0", "opened-ports"]
    _, opened_ports, _ = await ops_test.juju(*juju_cmd)
    assert opened_ports.strip() == f"{WORKLOAD_PORT}/tcp"
    assert (
        requests.get(
            f"http://{traefik_ip}",
            headers={"Host": f"{ops_test.model_name}-{go_app.name}.{external_hostname}"},
            timeout=5,
        ).status_code
        == 200
    )

    new_port = WORKLOAD_PORT + 10
    await go_app.set_config({"app-port": str(new_port)})
    await model.wait_for_idle(apps=[go_app.name, traefik_app.name], status="active")

    _, opened_ports, _ = await ops_test.juju(*juju_cmd)
    assert opened_ports.strip() == f"{new_port}/tcp"
    assert (
        requests.get(
            f"http://{traefik_ip}",
            headers={"Host": f"{ops_test.model_name}-{go_app.name}.{external_hostname}"},
            timeout=5,
        ).status_code
        == 200
    )

    await go_app.set_config({"app-port": str(WORKLOAD_PORT)})
    await model.wait_for_idle(apps=[go_app.name, traefik_app.name], status="active")

    _, opened_ports, _ = await ops_test.juju(*juju_cmd)
    assert opened_ports.strip() == f"{WORKLOAD_PORT}/tcp"
    assert (
        requests.get(
            f"http://{traefik_ip}",
            headers={"Host": f"{ops_test.model_name}-{go_app.name}.{external_hostname}"},
            timeout=5,
        ).status_code
        == 200
    )
