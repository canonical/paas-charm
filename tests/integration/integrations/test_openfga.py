# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import logging

import pytest
import requests
from juju.application import Application
from juju.errors import JujuError
from juju.model import Model
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "openfga_app_fixture, port",
    [
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
    ],
)
async def test_openfga_integrations(
    ops_test: OpsTest,
    openfga_app_fixture: Application,
    port,
    model: Model,
    get_unit_ips,
    request: pytest.FixtureRequest,
    openfga_server_app: Application,
    postgresql_k8s: Application,
):
    """
    arrange: Build and deploy the charm. Integrate the charm with OpenFGA.
    act: Send a read authorization models request from the charm.
    assert: The request succeeds.
    """
    openfga_app = request.getfixturevalue(openfga_app_fixture)
    await model.wait_for_idle()

    await model.add_relation(openfga_app.name, f"{openfga_server_app.name}:openfga")
    await model.wait_for_idle(
        idle_period=30,
        apps=[openfga_app.name, openfga_server_app.name, postgresql_k8s.name],
        status="active",
    )

    unit_ip = (await get_unit_ips(openfga_app.name))[0]
    response = requests.get(
        f"http://{unit_ip}:{port}/openfga/list-authorization-models", timeout=5
    )
    assert "Listed authorization models" in response.text
    assert response.status_code == 200
