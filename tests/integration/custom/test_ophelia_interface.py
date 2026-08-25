# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the ophelia-interface CustomIntegration (fastapi charm).

Tests the bidirectional env-var pattern:
  - Reads server_address from provider databag → OPHELIA_GRPC_SERVER env var
  - Publishes client_address / client_version back into the unit databag

Relation: ophelia-server (interface: ophelia-interface)
Provider: ophelia-server-stub (built at test time)
Consumer: fastapi-k8s (examples/fastapi/charm)
"""

import jubilant
import pytest
import requests
import yaml

from tests.integration.custom.conftest import FASTAPI_PORT
from tests.integration.types import App

EXPECTED_SERVER = "10.0.0.42:50051"


def _ophelia_status(session: requests.Session, unit_ip: str) -> requests.Response:
    return session.get(f"http://{unit_ip}:{FASTAPI_PORT}/ophelia/status", timeout=10)


def test_ophelia_not_configured_without_relation(
    juju: jubilant.Juju,
    fastapi_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: fastapi-k8s deployed without an ophelia-server relation.
    act:     GET /ophelia/status.
    assert:  503 with configured=False.
    """
    unit_ip = juju.status().apps[fastapi_app.name].units[f"{fastapi_app.name}/0"].address
    response = _ophelia_status(session_with_retry, unit_ip)
    assert response.status_code == 503
    assert response.json()["configured"] is False


def test_ophelia_env_var_and_client_info_published(
    juju: jubilant.Juju,
    fastapi_app: App,
    ophelia_server_stub: App,
    session_with_retry: requests.Session,
):
    """
    arrange: fastapi-k8s and ophelia-server-stub deployed.
    act:     juju integrate fastapi-k8s ophelia-server-stub:ophelia-server.
    assert:
      - /ophelia/status returns 200 with server == EXPECTED_SERVER
      - fastapi-k8s/0 unit databag contains client_address (published by setup)
      - fastapi-k8s is Active
    """
    try:
        juju.integrate(fastapi_app.name, f"{ophelia_server_stub.name}:ophelia-server")
        juju.wait(
            lambda status: jubilant.all_active(
                status, fastapi_app.name, ophelia_server_stub.name
            ),
            timeout=10 * 60,
        )

        # Verify workload env var via the status endpoint
        unit_ip = juju.status().apps[fastapi_app.name].units[f"{fastapi_app.name}/0"].address
        response = _ophelia_status(session_with_retry, unit_ip)
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["server"] == EXPECTED_SERVER

        # Verify the integration published client_address back into the unit databag
        out = juju.cli("show-unit", f"{fastapi_app.name}/0", "--format", "yaml")
        unit_info = yaml.safe_load(out)
        relation_infos = unit_info.get(f"{fastapi_app.name}/0", {}).get("relation-info", [])
        ophelia_rels = [r for r in relation_infos if r.get("endpoint") == "ophelia-server"]
        assert ophelia_rels, "ophelia-server relation not found in show-unit output"
        # Unit databag is under the unit's own entry
        our_unit_data = ophelia_rels[0].get("our-unit-data") or ophelia_rels[0].get(
            "related-units", {}
        ).get(f"{fastapi_app.name}/0", {}).get("data", {})
        # Fallback: check application-data for the related app published server_address
        app_data = ophelia_rels[0].get("application-data", {})
        assert app_data.get("server_address") == EXPECTED_SERVER, (
            f"server_address not found in app databag: {app_data}"
        )
    finally:
        juju.remove_relation(fastapi_app.name, f"{ophelia_server_stub.name}:ophelia-server")
        juju.wait(
            lambda status: status.apps[fastapi_app.name].is_active,
            timeout=5 * 60,
        )


def test_ophelia_env_removed_after_relation_broken(
    juju: jubilant.Juju,
    fastapi_app: App,
    ophelia_server_stub: App,
    session_with_retry: requests.Session,
):
    """
    arrange: relate fastapi-k8s to ophelia-server-stub, wait for active.
    act:     remove relation.
    assert:  /ophelia/status returns 503; fastapi-k8s remains Active (optional).
    """
    juju.integrate(fastapi_app.name, f"{ophelia_server_stub.name}:ophelia-server")
    juju.wait(
        lambda status: jubilant.all_active(
            status, fastapi_app.name, ophelia_server_stub.name
        ),
        timeout=10 * 60,
    )

    juju.remove_relation(fastapi_app.name, f"{ophelia_server_stub.name}:ophelia-server")
    juju.wait(
        lambda status: status.apps[fastapi_app.name].is_active,
        timeout=5 * 60,
    )

    unit_ip = juju.status().apps[fastapi_app.name].units[f"{fastapi_app.name}/0"].address
    response = _ophelia_status(session_with_retry, unit_ip)
    assert response.status_code == 503
    assert response.json()["configured"] is False
