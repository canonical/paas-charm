# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the nginx-route CustomIntegration (expressjs charm).

Tests the side-effect pattern:
  require_nginx_route(charm=handle.charm, ...) publishes service routing config
  to nginx-ingress-integrator. No workload environment variables are produced.

Relation: nginx-route (interface: nginx-route)
Provider: nginx-ingress-integrator (from Charmhub)
Consumer: expressjs-k8s (examples/expressjs/charm)
"""

import jubilant
import pytest
import requests
import yaml

from tests.integration.custom.conftest import EXPRESSJS_PORT
from tests.integration.types import App


def test_nginx_route_charm_stays_active(
    juju: jubilant.Juju,
    expressjs_app: App,
    nginx_ingress_integrator_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: expressjs-k8s and nginx-ingress-integrator deployed.
    act:     juju integrate expressjs-k8s nginx-ingress-integrator:nginx-route.
    assert:  expressjs-k8s remains Active — side-effect integration never blocks workload.
    """
    try:
        juju.integrate(
            expressjs_app.name, f"{nginx_ingress_integrator_app.name}:nginx-route"
        )
        juju.wait(
            lambda status: status.apps[expressjs_app.name].is_active,
            timeout=5 * 60,
        )
        assert juju.status().apps[expressjs_app.name].is_active
    finally:
        juju.remove_relation(
            expressjs_app.name, f"{nginx_ingress_integrator_app.name}:nginx-route"
        )
        juju.wait(
            lambda status: status.apps[expressjs_app.name].is_active,
            timeout=5 * 60,
        )


def test_nginx_route_relation_data_published(
    juju: jubilant.Juju,
    expressjs_app: App,
    nginx_ingress_integrator_app: App,
):
    """
    arrange: expressjs-k8s related to nginx-ingress-integrator.
    act:     inspect the relation application databag.
    assert:  NginxRouteIntegration published service-name, service-hostname,
             and service-port into the app databag (as required by the nginx-route
             interface contract).
    """
    try:
        juju.integrate(
            expressjs_app.name, f"{nginx_ingress_integrator_app.name}:nginx-route"
        )
        juju.wait(
            lambda status: status.apps[expressjs_app.name].is_active,
            timeout=5 * 60,
        )

        out = juju.cli("show-unit", f"{expressjs_app.name}/0", "--format", "yaml")
        unit_info = yaml.safe_load(out)
        relation_infos = (
            unit_info.get(f"{expressjs_app.name}/0", {}).get("relation-info", [])
        )
        nginx_rels = [r for r in relation_infos if r.get("endpoint") == "nginx-route"]
        assert nginx_rels, "nginx-route relation not found in show-unit output"

        app_data = nginx_rels[0].get("application-data", {})
        assert "service-name" in app_data, f"service-name missing from app databag: {app_data}"
        assert "service-hostname" in app_data, (
            f"service-hostname missing from app databag: {app_data}"
        )
        assert "service-port" in app_data, (
            f"service-port missing from app databag: {app_data}"
        )
        assert str(app_data["service-port"]).isdigit(), (
            f"service-port should be numeric: {app_data['service-port']}"
        )
    finally:
        juju.remove_relation(
            expressjs_app.name, f"{nginx_ingress_integrator_app.name}:nginx-route"
        )
        juju.wait(
            lambda status: status.apps[expressjs_app.name].is_active,
            timeout=5 * 60,
        )


def test_nginx_route_no_env_vars_added(
    juju: jubilant.Juju,
    expressjs_app: App,
    nginx_ingress_integrator_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: expressjs-k8s related to nginx-ingress-integrator.
    act:     GET / on the expressjs workload.
    assert:  Workload responds normally; no NGINX_* variables in the environment
             (side-effect integrations produce no env vars).
    """
    try:
        juju.integrate(
            expressjs_app.name, f"{nginx_ingress_integrator_app.name}:nginx-route"
        )
        juju.wait(
            lambda status: status.apps[expressjs_app.name].is_active,
            timeout=5 * 60,
        )
        unit_ip = (
            juju.status().apps[expressjs_app.name]
            .units[f"{expressjs_app.name}/0"].address
        )
        response = session_with_retry.get(
            f"http://{unit_ip}:{EXPRESSJS_PORT}/", timeout=10
        )
        assert response.status_code == 200
    finally:
        juju.remove_relation(
            expressjs_app.name, f"{nginx_ingress_integrator_app.name}:nginx-route"
        )
        juju.wait(
            lambda status: status.apps[expressjs_app.name].is_active,
            timeout=5 * 60,
        )
