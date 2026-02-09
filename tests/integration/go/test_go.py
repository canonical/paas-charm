#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Go charm."""

import logging

import jubilant
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)
WORKLOAD_PORT = 8080


def test_go_is_up(go_app: App, session_with_retry: requests.Session, juju: jubilant.Juju):
    """
    arrange: build and deploy the go charm.
    act: send a request to the go application managed by the go charm.
    assert: the go application should return a correct response.
    """
    status = juju.status()
    for unit in status.apps[go_app.name].units.values():
        response = session_with_retry.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


def test_user_defined_config(
    go_app: App, session_with_retry: requests.Session, juju: jubilant.Juju
):
    """
    arrange: build and deploy the go charm. Set the config user-defined-config to a new value.
    act: call the endpoint to get the value of the env variable related to the config.
    assert: the value of the env variable and the config should match.
    """
    juju.config(go_app.name, {"user-defined-config": "newvalue"})
    juju.wait(lambda status: jubilant.all_active(status, go_app.name, "postgresql-k8s"))

    status = juju.status()
    for unit in status.apps[go_app.name].units.values():
        response = session_with_retry.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/env/user-defined-config", timeout=5
        )
        assert response.status_code == 200
        assert "newvalue" in response.text


def test_migration(go_app: App, session_with_retry: requests.Session, juju: jubilant.Juju):
    """
    arrange: build and deploy the go charm with postgresql integration.
    act: send a request to an endpoint that uses the table created by the migration script.
    assert: the go application should return a correct response.
    """
    status = juju.status()
    for unit in status.apps[go_app.name].units.values():
        response = session_with_retry.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/postgresql/migratestatus", timeout=5
        )
        assert response.status_code == 200
        assert "SUCCESS" in response.text


def test_open_ports(
    juju: jubilant.Juju,
    go_app: App,
    traefik_app: App,
    session_with_retry: requests.Session,
    external_hostname: str,
):
    """
    arrange: after Go charm has been deployed.
    act: integrate with the traefik charm with the ingress integration and change app-port configuration.
    assert: charm opened ports should change accordingly.
    """
    # Integrate go with traefik
    try:
        juju.integrate(traefik_app.name, go_app.name)
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    juju.wait(lambda status: jubilant.all_active(status, go_app.name, traefik_app.name))

    status = juju.status()
    traefik_ip = list(status.apps[traefik_app.name].units.values())[0].address

    # Check initial opened ports
    opened_ports = juju.cli("exec", "--unit", f"{go_app.name}/0", "opened-ports")
    assert opened_ports.strip() == f"{WORKLOAD_PORT}/tcp"
    assert (
        session_with_retry.get(
            f"http://{traefik_ip}",
            headers={"Host": f"{juju.model}-{go_app.name}.{external_hostname}"},
            timeout=5,
        ).status_code
        == 200
    )

    # Change port configuration
    new_port = WORKLOAD_PORT + 10
    juju.config(go_app.name, {"app-port": str(new_port)})
    juju.wait(lambda status: jubilant.all_active(status, go_app.name, traefik_app.name))

    opened_ports = juju.cli("exec", "--unit", f"{go_app.name}/0", "opened-ports")
    assert opened_ports.strip() == f"{new_port}/tcp"
    assert (
        session_with_retry.get(
            f"http://{traefik_ip}",
            headers={"Host": f"{juju.model}-{go_app.name}.{external_hostname}"},
            timeout=5,
        ).status_code
        == 200
    )

    # Restore original port
    juju.config(go_app.name, {"app-port": str(WORKLOAD_PORT)})
    juju.wait(lambda status: jubilant.all_active(status, go_app.name, traefik_app.name))

    opened_ports = juju.cli("exec", "--unit", f"{go_app.name}/0", "opened-ports")
    assert opened_ports.strip() == f"{WORKLOAD_PORT}/tcp"
    assert (
        session_with_retry.get(
            f"http://{traefik_ip}",
            headers={"Host": f"{juju.model}-{go_app.name}.{external_hostname}"},
            timeout=5,
        ).status_code
        == 200
    )
