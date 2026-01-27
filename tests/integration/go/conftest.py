# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for go charm integration tests."""

import os
import pathlib

import jubilant
import pytest

from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/go/charm")


@pytest.fixture(scope="module", name="traefik_app")
def deploy_traefik_fixture(
    juju: jubilant.Juju,
    traefik_app_name: str,
    external_hostname: str,
):
    """Deploy traefik."""
    if not juju.status().apps.get(traefik_app_name):
        juju.deploy(
            "traefik-k8s",
            app=traefik_app_name,
            channel="edge",
            trust=True,
            config={
                "external_hostname": external_hostname,
                "routing_mode": "subdomain",
            },
        )
    juju.wait(
        lambda status: status.apps[traefik_app_name].is_active,
        error=jubilant.any_blocked,
    )
    return App(traefik_app_name)
