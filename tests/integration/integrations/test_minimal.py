# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import logging
import pathlib

import pytest
import requests
from juju.model import Model
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import inject_venv

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

logger = logging.getLogger(__name__)


async def test_flask_minimal(
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
    example_app = "flask-minimal"
    test_flask_image = pytestconfig.getoption(f"--{example_app}-app-image")
    if not test_flask_image:
        raise ValueError(f"the following arguments are required: --{example_app}-app-image")

    resources = {
        "flask-app-image": test_flask_image,
    }
    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"/{example_app}-k8s" in f), None
    )

    if not charm_file:
        charm_location = PROJECT_ROOT / f"examples/{example_app}/charm"
        charm_file = await ops_test.build_charm(charm_location)
    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    await model.deploy(
        pathlib.Path(charm_file).absolute(),
        resources=resources,
        application_name=f"{example_app}-k8s",
        series="jammy",
    )
    await model.wait_for_idle()

    unit_ip = (await get_unit_ips(f"{example_app}-k8s"))[0]
    response = requests.get(f"http://{unit_ip}:8000/", timeout=5)
    assert "Hello" in response.text
    assert response.status_code == 200
