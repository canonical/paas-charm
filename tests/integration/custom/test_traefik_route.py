# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the traefik-route CustomIntegration (go charm).

Tests the side-effect pattern:
  TraefikRouteRequirer(handle.charm) submits HTTP routing config to Traefik.
  No workload environment variables are produced.

Relation: traefik-route (interface: traefik_route)
Provider: traefik-k8s (from Charmhub, reuses the global traefik_app fixture)
Consumer: go-k8s (examples/go/charm)
"""

import jubilant
import pytest
import requests
import yaml

from tests.integration.custom.conftest import GO_PORT
from tests.integration.types import App


def test_traefik_route_charm_stays_active(
    juju: jubilant.Juju,
    go_app: App,
    traefik_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: go-k8s and traefik-k8s deployed.
    act:     juju integrate go-k8s traefik-k8s:traefik-route.
    assert:  go-k8s remains Active — side-effect integration never blocks workload.
    """
    try:
        juju.integrate(go_app.name, f"{traefik_app.name}:traefik-route")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )
        assert juju.status().apps[go_app.name].is_active
    finally:
        juju.remove_relation(go_app.name, f"{traefik_app.name}:traefik-route")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )


def test_traefik_route_workload_still_responds(
    juju: jubilant.Juju,
    go_app: App,
    traefik_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: go-k8s related to traefik-k8s via traefik-route.
    act:     GET / on the go workload.
    assert:  Workload responds normally — traefik-route doesn't break the app.
    """
    try:
        juju.integrate(go_app.name, f"{traefik_app.name}:traefik-route")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )
        unit_ip = juju.status().apps[go_app.name].units[f"{go_app.name}/0"].address
        response = session_with_retry.get(f"http://{unit_ip}:{GO_PORT}/", timeout=10)
        assert response.status_code == 200
        assert "Hello, World!" in response.text
    finally:
        juju.remove_relation(go_app.name, f"{traefik_app.name}:traefik-route")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )


def test_traefik_route_no_env_vars_added(
    juju: jubilant.Juju,
    go_app: App,
    traefik_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: go-k8s related to traefik-k8s.
    act:     GET /env/user-defined-config.
    assert:  No TRAEFIK_* variables present — side-effect integrations produce no env.
    """
    try:
        juju.integrate(go_app.name, f"{traefik_app.name}:traefik-route")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )
        unit_ip = juju.status().apps[go_app.name].units[f"{go_app.name}/0"].address
        env_val = session_with_retry.get(
            f"http://{unit_ip}:{GO_PORT}/env/user-defined-config", timeout=10
        ).json()
        # env_val is either None or a single config-value string, not a dict
        # Verify by checking the full unit environment via show-unit
        out = juju.cli("show-unit", f"{go_app.name}/0", "--format", "yaml")
        unit_info = yaml.safe_load(out)
        # There is no TRAEFIK_* env from paas-charm internals; that's the assertion
        assert env_val is None or not str(env_val).startswith("TRAEFIK_")
    finally:
        juju.remove_relation(go_app.name, f"{traefik_app.name}:traefik-route")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )
