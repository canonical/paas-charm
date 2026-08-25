# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the github-runner-planner CustomIntegration (go charm).

Tests the side-effect + reconcile pattern:
  GithubRunnerPlannerIntegration publishes the charm's base URL as the
  ``endpoint`` in the planner relation app databag on every restart
  (via reconcile()). The requirer (runner-manager) reads this endpoint
  to configure its Planner client.

Relation: planner (interface: github_runner_planner_v0)
Requirer:  planner-stub (built at test time)
Provider:  go-k8s (examples/go/charm) — this side provides the endpoint

Note: This is an illustrative integration. The full planner charm also
creates per-relation auth tokens via the Planner HTTP API and reconciles
flavor configurations, which are out of scope here.
"""

import jubilant
import pytest
import requests
import yaml

from tests.integration.custom.conftest import GO_PORT
from tests.integration.types import App


def test_planner_charm_stays_active_after_relate(
    juju: jubilant.Juju,
    go_app: App,
    planner_requirer_stub: App,
    session_with_retry: requests.Session,
):
    """
    arrange: go-k8s and planner-stub deployed.
    act:     juju integrate go-k8s planner-stub:planner.
    assert:  go-k8s remains Active — planner is optional and never blocks workload.
    """
    try:
        juju.integrate(go_app.name, f"{planner_requirer_stub.name}:planner")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )
        assert juju.status().apps[go_app.name].is_active
    finally:
        juju.remove_relation(go_app.name, f"{planner_requirer_stub.name}:planner")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )


def test_planner_endpoint_published_by_reconcile(
    juju: jubilant.Juju,
    go_app: App,
    planner_requirer_stub: App,
):
    """
    arrange: go-k8s related to planner-stub; charm is Active.
    act:     inspect relation application databag on go-k8s/0.
    assert:  reconcile() published ``endpoint`` into the app databag with a
             non-empty value (the charm's base URL for the Planner API).
    """
    try:
        juju.integrate(go_app.name, f"{planner_requirer_stub.name}:planner")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )

        out = juju.cli("show-unit", f"{go_app.name}/0", "--format", "yaml")
        unit_info = yaml.safe_load(out)
        relation_infos = unit_info.get(f"{go_app.name}/0", {}).get("relation-info", [])
        planner_rels = [r for r in relation_infos if r.get("endpoint") == "planner"]
        assert planner_rels, "planner relation not found in show-unit output"

        app_data = planner_rels[0].get("application-data", {})
        assert "endpoint" in app_data, (
            f"reconcile() should have published 'endpoint' into app databag.\n"
            f"App databag: {app_data}"
        )
        assert app_data["endpoint"], "endpoint should be non-empty"
    finally:
        juju.remove_relation(go_app.name, f"{planner_requirer_stub.name}:planner")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )


def test_planner_workload_still_responds(
    juju: jubilant.Juju,
    go_app: App,
    planner_requirer_stub: App,
    session_with_retry: requests.Session,
):
    """
    arrange: go-k8s related to planner-stub.
    act:     GET / on the go workload.
    assert:  Workload responds normally — planner reconcile doesn't break the app.
    """
    try:
        juju.integrate(go_app.name, f"{planner_requirer_stub.name}:planner")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )
        unit_ip = juju.status().apps[go_app.name].units[f"{go_app.name}/0"].address
        response = session_with_retry.get(f"http://{unit_ip}:{GO_PORT}/", timeout=10)
        assert response.status_code == 200
        assert "Hello, World!" in response.text
    finally:
        juju.remove_relation(go_app.name, f"{planner_requirer_stub.name}:planner")
        juju.wait(
            lambda status: status.apps[go_app.name].is_active,
            timeout=5 * 60,
        )
