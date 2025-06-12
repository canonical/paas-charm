#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Springboot SAML test."""

import logging

import jubilant
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8080


def test_springboot_saml_integration(
    juju: jubilant.Juju,
    spring_boot_app: App,
    saml_integrator: App,
    spring_boot_unit_ip: str,
    http: requests.Session,
):
    """
    arrange: integrate the spring boot charm with SAML integrator.
    act: call the samltest endpoint.
    assert: the charm should be redirected to IdP and when logged in should return 200.
    """
    juju.integrate(spring_boot_app.name, saml_integrator.name)
    juju.wait(
        lambda status: jubilant.all_active(status, saml_integrator.name, spring_boot_app.name),
        timeout=10 * 60,
    )
    response = http.get(f"http://{spring_boot_unit_ip}:{WORKLOAD_PORT}/samltest", timeout=5)
    assert response.status_code == 200
    assert "simplesaml" in response.text
