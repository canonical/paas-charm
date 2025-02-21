# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for go charm integration tests."""
import os
import pathlib

import pytest
import pytest_asyncio
from juju.model import Model
from pytest import Config
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import inject_venv

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/go/charm")


@pytest.fixture(scope="module", name="go_app_image")
def fixture_go_app_image(pytestconfig: Config):
    """Return the --go-app-image test parameter."""
    image = pytestconfig.getoption("--go-app-image")
    if not image:
        raise ValueError("the following arguments are required: --go-app-image")
    return image


@pytest_asyncio.fixture(scope="module", name="charm_file")
async def charm_file_fixture(
    pytestconfig: pytest.Config, ops_test: OpsTest, tmp_path_factory
) -> str:
    """Get the existing charm file."""
    charm_file = next((f for f in pytestconfig.getoption("--charm-file") if "/go-k8s" in f), None)
    if not charm_file:
        charm_file = await ops_test.build_charm(PROJECT_ROOT / "examples/go/charm")
    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    return pathlib.Path(charm_file).absolute()


@pytest_asyncio.fixture(scope="module", name="go_app")
async def go_app_fixture(charm_file: str, model: Model, go_app_image: str, postgresql_k8s):
    """Build and deploy the go charm."""
    app_name = "go-k8s"

    resources = {
        "app-image": go_app_image,
    }
    app = await model.deploy(
        charm_file,
        application_name=app_name,
        resources=resources,
    )
    await model.integrate(app_name, "postgresql-k8s")
    await model.wait_for_idle(status="active")
    return app
