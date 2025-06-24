# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for OpenFGA integration."""

import logging

import jubilant
import pytest

from tests.integration.helpers import check_openfga_auth_models_patiently
from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("spring_boot_app", 8080),
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
    ],
)
def test_openfga_integrations(
    juju: jubilant.Juju,
    app_fixture: App,
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
    app = request.getfixturevalue(app_fixture)
    juju.wait(lambda status: jubilant.all_active(status, app.name, openfga_server_app.name))

    juju.integrate(app.name, f"{openfga_server_app.name}:openfga")
    juju.wait(
        lambda status: jubilant.all_active(
            status, app.name, openfga_server_app.name, postgresql_k8s.name
        )
    )

    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address
    check_openfga_auth_models_patiently(unit_ip, port)
