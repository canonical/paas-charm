# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for FastAPI charm integration tests."""

import os
import pathlib

import jubilant
import pytest
from pytest import Config

from tests.integration.conftest import generate_app_fixture

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/fastapi/charm")


@pytest.fixture(scope="module", name="fastapi_app_image")
def fixture_fastapi_app_image(pytestconfig: Config):
    """Return the --fastapi-app-image test parameter."""
    image = pytestconfig.getoption("--fastapi-app-image")
    if not image:
        raise ValueError("the following arguments are required: --fastapi-app-image")
    return image


@pytest.fixture(scope="module", name="fastapi_app")
def fastapi_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    fastapi_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the fastapi charm."""
    framework = "fastapi"
    yield from generate_app_fixture(
        juju=juju,
        pytestconfig=pytestconfig,
        framework=framework,
        tmp_path_factory=tmp_path_factory,
        use_postgres=True,
        config={"non-optional-string": "non-optional-value"},
        resources={
            "app-image": fastapi_app_image,
        },
    )
