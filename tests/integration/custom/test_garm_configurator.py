# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the garm-configurator CustomIntegration (go charm).

Tests the side-effect + TOML-file pattern:
  GarmConfiguratorIntegration reads OpenStack provider config from relation
  unit databags, renders a TOML config file, and pushes it to
  /etc/garm/config.toml in the container via reconcile().
  The go workload exposes GET /garm-config to read back the file.

Relation: garm-configurator (interface: garm_configurator_v0)
Provider: garm-configurator-stub (built at test time)
Consumer: go-k8s-garm (go-k8s with garm-configurator declared required)

Note: This is an illustrative integration. The full garm charm additionally
performs GARM admin initialisation and scaleset reconciliation via the GARM
HTTP API, which are out of scope here.
"""

import jubilant
import pytest
import requests

from tests.integration.custom.conftest import GO_PORT
from tests.integration.types import App

# Sections that must appear in a valid GARM TOML config
EXPECTED_TOML_SECTIONS = [
    "[apiserver]",
    "[database]",
    "[jwt_auth]",
    "provider_type",
]


def test_garm_blocked_without_configurator(
    juju: jubilant.Juju,
    go_app_garm: App,
    session_with_retry: requests.Session,
):
    """
    arrange: go-k8s-garm deployed with garm-configurator required (optional=False).
    act:     no garm-configurator relation exists yet.
    assert:
      - Charm is not Active (Waiting or Blocked).
      - GET /garm-config returns 503 — config file not yet written.
    """
    status = juju.status()
    assert not status.apps[go_app_garm.name].is_active, (
        f"Expected go-k8s-garm to be blocked/waiting without garm-configurator, "
        f"got: {status.apps[go_app_garm.name].app_status.status}"
    )

    unit_ip = status.apps[go_app_garm.name].units[f"{go_app_garm.name}/0"].address
    response = session_with_retry.get(
        f"http://{unit_ip}:{GO_PORT}/garm-config", timeout=10
    )
    assert response.status_code == 503


def test_garm_toml_written_after_relate(
    juju: jubilant.Juju,
    go_app_garm: App,
    garm_configurator_stub: App,
    session_with_retry: requests.Session,
):
    """
    arrange: go-k8s-garm and garm-configurator-stub deployed.
    act:     juju integrate go-k8s-garm garm-configurator-stub:garm-configurator.
    assert:
      - go-k8s-garm becomes Active.
      - GET /garm-config returns 200 with valid TOML content.
      - TOML body contains [apiserver], [database], [jwt_auth], provider_type.
    """
    try:
        juju.integrate(
            go_app_garm.name, f"{garm_configurator_stub.name}:garm-configurator"
        )
        juju.wait(
            lambda status: status.apps[go_app_garm.name].is_active,
            timeout=10 * 60,
        )

        unit_ip = (
            juju.status().apps[go_app_garm.name]
            .units[f"{go_app_garm.name}/0"].address
        )
        response = session_with_retry.get(
            f"http://{unit_ip}:{GO_PORT}/garm-config", timeout=10
        )
        assert response.status_code == 200, (
            f"Expected 200 from /garm-config, got {response.status_code}: {response.text}"
        )
        body = response.text
        for section in EXPECTED_TOML_SECTIONS:
            assert section in body, (
                f"Expected TOML section/key '{section}' in /garm-config output.\n"
                f"Full response:\n{body}"
            )
    finally:
        juju.remove_relation(
            go_app_garm.name, f"{garm_configurator_stub.name}:garm-configurator"
        )
        juju.wait(
            lambda status: not status.apps[go_app_garm.name].is_active,
            timeout=5 * 60,
        )


def test_garm_toml_gone_after_relation_broken(
    juju: jubilant.Juju,
    go_app_garm: App,
    garm_configurator_stub: App,
    session_with_retry: requests.Session,
):
    """
    arrange: relate go-k8s-garm to garm-configurator-stub; wait active.
    act:     remove the relation.
    assert:
      - go-k8s-garm returns to Blocked/Waiting (required relation gone).
      - GET /garm-config returns 503 — charm no longer active, config stale.
    """
    # Establish relation
    juju.integrate(
        go_app_garm.name, f"{garm_configurator_stub.name}:garm-configurator"
    )
    juju.wait(
        lambda status: status.apps[go_app_garm.name].is_active,
        timeout=10 * 60,
    )

    # Remove relation
    juju.remove_relation(
        go_app_garm.name, f"{garm_configurator_stub.name}:garm-configurator"
    )
    juju.wait(
        lambda status: not status.apps[go_app_garm.name].is_active,
        timeout=5 * 60,
    )

    assert not juju.status().apps[go_app_garm.name].is_active

    unit_ip = (
        juju.status().apps[go_app_garm.name].units[f"{go_app_garm.name}/0"].address
    )
    response = session_with_retry.get(
        f"http://{unit_ip}:{GO_PORT}/garm-config", timeout=10
    )
    assert response.status_code == 503
