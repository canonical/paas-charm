# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the temporal-host-info CustomIntegration (flask charm).

Tests the env-var pattern:
  TemporalHostInfoRequirer(handle.charm) → TEMPORAL_HOST / TEMPORAL_PORT
  exposed via GET /temporal/status on the workload.

Relation: temporal-host-info (interface: temporal-host-info)
Provider: temporal-k8s (from Charmhub)
Consumer: flask-k8s (examples/flask/charm)
"""

import jubilant
import pytest
import requests

from tests.integration.custom.conftest import FLASK_PORT
from tests.integration.types import App


def _temporal_status(session: requests.Session, unit_ip: str) -> requests.Response:
    return session.get(f"http://{unit_ip}:{FLASK_PORT}/temporal/status", timeout=10)


def test_temporal_not_configured_without_relation(
    juju: jubilant.Juju,
    flask_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: flask-k8s deployed without a temporal-host-info relation.
    act:     GET /temporal/status.
    assert:  503 response with configured=False (env vars not yet set).
    """
    unit_ip = juju.status().apps[flask_app.name].units[f"{flask_app.name}/0"].address
    response = _temporal_status(session_with_retry, unit_ip)
    assert response.status_code == 503
    assert response.json()["configured"] is False


def test_temporal_env_vars_set_after_relate(
    juju: jubilant.Juju,
    flask_app: App,
    temporal_k8s_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: flask-k8s and temporal-k8s both deployed, no relation yet.
    act:     juju integrate flask-k8s temporal-k8s:temporal-host-info.
    assert:  /temporal/status returns 200 with host and port populated;
             flask-k8s is Active.
    """
    try:
        juju.integrate(flask_app.name, f"{temporal_k8s_app.name}:temporal-host-info")
        juju.wait(
            lambda status: jubilant.all_active(
                status, flask_app.name, temporal_k8s_app.name
            ),
            timeout=10 * 60,
        )
        unit_ip = juju.status().apps[flask_app.name].units[f"{flask_app.name}/0"].address
        response = _temporal_status(session_with_retry, unit_ip)
        assert response.status_code == 200
        data = response.json()
        assert data["configured"] is True
        assert data["host"], "TEMPORAL_HOST should be non-empty"
        assert data["port"], "TEMPORAL_PORT should be non-empty"
    finally:
        juju.remove_relation(flask_app.name, f"{temporal_k8s_app.name}:temporal-host-info")
        juju.wait(
            lambda status: status.apps[flask_app.name].is_active,
            timeout=5 * 60,
        )


def test_temporal_env_removed_after_relation_broken(
    juju: jubilant.Juju,
    flask_app: App,
    temporal_k8s_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: relate flask-k8s to temporal-k8s, wait for active.
    act:     remove the relation.
    assert:  /temporal/status returns 503 again once the relation is gone;
             flask-k8s remains Active (relation is optional).
    """
    juju.integrate(flask_app.name, f"{temporal_k8s_app.name}:temporal-host-info")
    juju.wait(
        lambda status: jubilant.all_active(
            status, flask_app.name, temporal_k8s_app.name
        ),
        timeout=10 * 60,
    )

    juju.remove_relation(flask_app.name, f"{temporal_k8s_app.name}:temporal-host-info")
    juju.wait(
        lambda status: status.apps[flask_app.name].is_active,
        timeout=5 * 60,
    )

    unit_ip = juju.status().apps[flask_app.name].units[f"{flask_app.name}/0"].address
    response = _temporal_status(session_with_retry, unit_ip)
    assert response.status_code == 503
    assert response.json()["configured"] is False
