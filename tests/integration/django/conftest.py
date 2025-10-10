# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""
import os
import pathlib

import pytest
import pytest_asyncio
from juju.application import Application
from juju.model import Model
from pytest import Config, FixtureRequest
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import inject_charm_config, inject_venv

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/django/charm")


@pytest.fixture(scope="module", name="django_app_image")
def fixture_django_app_image(pytestconfig: Config):
    """Return the --django-app-image test parameter."""
    image = pytestconfig.getoption("--django-app-image")
    if not image:
        raise ValueError("the following arguments are required: --django-app-image")
    return image


@pytest.fixture(scope="module", name="django_async_app_image")
def fixture_django_async_app_image(pytestconfig: Config):
    """Return the --django-async-app-image test parameter."""
    image = pytestconfig.getoption("--django-async-app-image")
    if not image:
        raise ValueError("the following arguments are required: --django-async-app-image")
    return image


@pytest_asyncio.fixture(scope="module", name="charm_file")
async def charm_file_fixture(
    pytestconfig: pytest.Config, ops_test: OpsTest, tmp_path_factory
) -> str:
    """Get the existing charm file."""
    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if "django-k8s" in f), None
    )
    if not charm_file:
        charm_file = await ops_test.build_charm(PROJECT_ROOT / "examples/django/charm")
    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    return inject_charm_config(
        charm_file,
        {
            "config": {
                "options": {
                    "allowed-hosts": {"type": "string"},
                    "webserver-worker-class": {"type": "string"},
                }
            }
        },
        tmp_path_factory.mktemp("django"),
    )


@pytest_asyncio.fixture(scope="module", name="django_app")
async def django_app_fixture(charm_file: str, model: Model, django_app_image: str, postgresql_k8s):
    """Build and deploy the django charm."""
    app_name = "django-k8s"

    resources = {
        "django-app-image": django_app_image,
    }
    app = await model.deploy(
        charm_file,
        application_name=app_name,
        config={"django-allowed-hosts": "*"},
        resources=resources,
        series="jammy",
    )
    await model.integrate(app_name, "postgresql-k8s:database")
    await model.wait_for_idle(status="active")
    return app


@pytest_asyncio.fixture(scope="module", name="django_async_app")
async def django_async_app_fixture(
    charm_file: str, model: Model, django_async_app_image: str, postgresql_k8s
):
    """Build and deploy the async django charm."""
    app_name = "django-async-k8s"

    resources = {
        "django-app-image": django_async_app_image,
    }
    app = await model.deploy(
        charm_file,
        application_name=app_name,
        config={"django-allowed-hosts": "*"},
        resources=resources,
        series="jammy",
    )
    await model.integrate(app_name, "postgresql-k8s:database")
    await model.wait_for_idle(status="active")
    return app


@pytest_asyncio.fixture
async def update_config(model: Model, request: FixtureRequest, django_app: Application):
    """Update the django application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    orig_config = {k: v.get("value") for k, v in (await django_app.get_config()).items()}
    request_config = {k: str(v) for k, v in request.param.items()}
    await django_app.set_config(request_config)
    await model.wait_for_idle(apps=[django_app.name])

    yield request_config

    await django_app.set_config(
        {k: v for k, v in orig_config.items() if k in request_config and v is not None}
    )
    await django_app.reset_config([k for k in request_config if orig_config[k] is None])
    await model.wait_for_idle(apps=[django_app.name])
