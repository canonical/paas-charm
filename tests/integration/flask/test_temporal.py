#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the Flask custom Temporal relation."""

import jubilant
import requests

from tests.integration.types import App

TEMPORAL_APP = "temporal-k8s"
TEMPORAL_ADMIN_APP = "temporal-admin-k8s"
POSTGRESQL_APP = "postgresql-k8s"
CERTIFICATES_APP = "self-signed-certificates"
TEMPORAL_HOST = "temporal.local.test"
TEMPORAL_PORT = "7233"


def _deploy_temporal(juju: jubilant.Juju) -> None:
    """Deploy and integrate the applications needed by Temporal."""
    deployed_apps = juju.status().apps
    if TEMPORAL_APP not in deployed_apps:
        juju.deploy(
            TEMPORAL_APP,
            channel="1.23/edge",
            config={
                "external-hostname": TEMPORAL_HOST,
                "global-rps-limit": 100,
                "num-history-shards": 1,
            },
        )
    if TEMPORAL_ADMIN_APP not in deployed_apps:
        juju.deploy(TEMPORAL_ADMIN_APP, channel="1.23/edge")
    if POSTGRESQL_APP not in deployed_apps:
        juju.deploy(POSTGRESQL_APP, channel="14/stable", trust=True)
    if CERTIFICATES_APP not in deployed_apps:
        juju.deploy(CERTIFICATES_APP, channel="latest/stable")

    juju.wait(
        lambda status: jubilant.all_active(status, POSTGRESQL_APP, CERTIFICATES_APP),
        timeout=20 * 60,
    )
    juju.integrate(
        f"{POSTGRESQL_APP}:certificates",
        f"{CERTIFICATES_APP}:certificates",
    )
    juju.wait(
        lambda status: jubilant.all_active(status, POSTGRESQL_APP, CERTIFICATES_APP),
        timeout=20 * 60,
    )

    juju.integrate(f"{TEMPORAL_APP}:db", f"{POSTGRESQL_APP}:database")
    juju.integrate(f"{TEMPORAL_APP}:visibility", f"{POSTGRESQL_APP}:database")
    juju.integrate(f"{TEMPORAL_APP}:admin", f"{TEMPORAL_ADMIN_APP}:admin")
    juju.integrate(
        f"{TEMPORAL_APP}:temporal-host-info",
        f"{TEMPORAL_ADMIN_APP}:temporal-host-info",
    )
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            TEMPORAL_APP,
            TEMPORAL_ADMIN_APP,
            POSTGRESQL_APP,
            CERTIFICATES_APP,
        )
        and jubilant.all_agents_idle(status),
        timeout=20 * 60,
    )


def test_temporal_relation_environment(
    juju: jubilant.Juju,
    flask_app: App,
    session_with_retry: requests.Session,
) -> None:
    """
    arrange: deploy a real Temporal server topology and the Flask charm.
    act: relate Flask to Temporal, then remove the relation.
    assert: Temporal environment variables are added and subsequently removed.
    """
    _deploy_temporal(juju)
    juju.integrate(
        f"{flask_app.name}:temporal-host-info",
        f"{TEMPORAL_APP}:temporal-host-info",
    )
    juju.wait(
        lambda status: jubilant.all_active(status, flask_app.name, TEMPORAL_APP)
        and jubilant.all_agents_idle(status, flask_app.name, TEMPORAL_APP),
        timeout=10 * 60,
    )

    flask_unit = juju.status().apps[flask_app.name].units[f"{flask_app.name}/0"]
    response = session_with_retry.get(f"http://{flask_unit.address}:8000/env", timeout=30)
    response.raise_for_status()
    environment = response.json()
    assert environment["TEMPORAL_HOST"] == TEMPORAL_HOST
    assert environment["TEMPORAL_PORT"] == TEMPORAL_PORT

    juju.remove_relation(
        f"{flask_app.name}:temporal-host-info",
        f"{TEMPORAL_APP}:temporal-host-info",
    )
    juju.wait(
        lambda status: status.apps[flask_app.name].is_active
        and jubilant.all_agents_idle(status, flask_app.name),
        timeout=10 * 60,
    )

    flask_unit = juju.status().apps[flask_app.name].units[f"{flask_app.name}/0"]
    response = session_with_retry.get(f"http://{flask_unit.address}:8000/env", timeout=30)
    response.raise_for_status()
    environment = response.json()
    assert "TEMPORAL_HOST" not in environment
    assert "TEMPORAL_PORT" not in environment
