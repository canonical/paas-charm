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


async def test_openfga_integrations(
    ops_test: OpsTest,
    model: Model,
    get_unit_ips,
    pytestconfig: pytest.Config,
):
    """
    arrange: Build and deploy the charm with minimal integrations.
    act: Send a request to the web application.
    assert: The request succeeds.
    """
    test_flask_image = pytestconfig.getoption("--flask-minimal-app-image")
    if not test_flask_image:
        raise ValueError("the following arguments are required: --test-flask-image")

    app_name = "flask-minimal-k8s"
    resources = {
        "flask-app-image": test_flask_image,
    }
    await model.deploy(build_charm, resources=resources, application_name=app_name, series="jammy")
    await model.wait_for_idle()

    unit_ip = (await get_unit_ips(app_name))[0]
    response = requests.get(f"http://{unit_ip}:{port}/", timeout=5)
    assert "Hello" in response.text
    assert response.status_code == 200
