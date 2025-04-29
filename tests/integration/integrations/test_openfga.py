# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "openfga_app_fixture, port",
    [
        ("flask_app", 8000),
        ("django_app", 8000),
    ],
)
def test_openfga_integrations(
    juju: jubilant.Juju,
    openfga_app_fixture: App,
    port,
    request: pytest.FixtureRequest,
    openfga_server_app: App,
    postgresql_k8s: App,
):
    """
    arrange: Build and deploy the charm. Integrate the charm with OpenFGA.
    act: Send a read authorization models request from the charm.
    assert: The request succeeds.
    """
    openfga_integrations(
        juju, openfga_app_fixture, port, request, openfga_server_app, postgresql_k8s
    )


@pytest.mark.parametrize(
    "openfga_app_fixture, port",
    [
        ("fastapi_app", 8080),
        ("go_app", 8080),
    ],
)
@pytest.mark.skip_juju_version("3.4")
def test_openfga_integrations_noble(
    juju: jubilant.Juju,
    openfga_app_fixture: App,
    port,
    request: pytest.FixtureRequest,
    openfga_server_app: App,
    postgresql_k8s: App,
):
    """
    arrange: Build and deploy the charm. Integrate the charm with OpenFGA.
    act: Send a read authorization models request from the charm.
    assert: The request succeeds.
    """
    openfga_integrations(
        juju, openfga_app_fixture, port, request, openfga_server_app, postgresql_k8s
    )


def openfga_integrations(
    juju: jubilant.Juju,
    openfga_app_fixture: App,
    port,
    request: pytest.FixtureRequest,
    openfga_server_app: App,
    postgresql_k8s: App,
):
    openfga_app = request.getfixturevalue(openfga_app_fixture)
    juju.wait(lambda status: status.apps[openfga_app.name].is_active)
    juju.wait(lambda status: status.apps[openfga_server_app.name].is_active)

    juju.integrate(openfga_app.name, f"{openfga_server_app.name}:openfga")
    juju.wait(lambda status: status.apps[openfga_app.name].is_active)
    juju.wait(lambda status: status.apps[openfga_server_app.name].is_active)
    juju.wait(lambda status: status.apps[postgresql_k8s.name].is_active)

    status = juju.status()
    unit_ip = status.apps[openfga_app.name].units[openfga_app.name + "/0"].address
    response = requests.get(
        f"http://{unit_ip}:{port}/openfga/list-authorization-models", timeout=5
    )
    assert "Listed authorization models" in response.text
    assert response.status_code == 200
