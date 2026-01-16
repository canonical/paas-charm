# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for Django charm integration tests."""
import os
import pathlib

import jubilant
import pytest
from pytest import Config

from tests.integration.conftest import build_charm_file
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    """Change working directory to Django charm."""
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


@pytest.fixture(scope="module", name="django_app")
def django_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    django_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the Django charm."""
    app_name = "django-k8s"

    resources = {
        "django-app-image": django_app_image,
    }

    # Deploy postgresql if not already deployed
    if not juju.status().apps.get("postgresql-k8s"):
        juju.deploy(
            "postgresql-k8s",
            channel="14/edge",
            base="ubuntu@22.04",
            trust=True,
            config={
                "profile": "testing",
                "plugin_hstore_enable": "true",
                "plugin_pg_trgm_enable": "true",
            },
        )

    charm_file = build_charm_file(pytestconfig, "django", tmp_path_factory)

    juju.deploy(
        charm=charm_file,
        app=app_name,
        resources=resources,
        config={"django-allowed-hosts": "*"},
        base="ubuntu@22.04",
    )
    juju.integrate(app_name, "postgresql-k8s:database")
    juju.wait(
        lambda status: jubilant.all_active(status, app_name, "postgresql-k8s"),
        timeout=300,
    )
    return App(app_name)


@pytest.fixture(scope="module", name="django_async_app")
def django_async_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    django_async_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the async Django charm."""
    app_name = "django-async-k8s"

    resources = {
        "django-app-image": django_async_app_image,
    }

    # Deploy postgresql if not already deployed
    if not juju.status().apps.get("postgresql-k8s"):
        juju.deploy(
            "postgresql-k8s",
            channel="14/edge",
            base="ubuntu@22.04",
            trust=True,
            config={
                "profile": "testing",
                "plugin_hstore_enable": "true",
                "plugin_pg_trgm_enable": "true",
            },
        )

    charm_file = build_charm_file(pytestconfig, "django", tmp_path_factory)

    juju.deploy(
        charm=charm_file,
        app=app_name,
        resources=resources,
        config={"django-allowed-hosts": "*"},
        base="ubuntu@22.04",
    )
    juju.integrate(app_name, "postgresql-k8s:database")
    juju.wait(
        lambda status: jubilant.all_active(status, app_name, "postgresql-k8s"),
        timeout=300,
    )
    return App(app_name)


@pytest.fixture
def update_config(juju: jubilant.Juju, request: pytest.FixtureRequest, django_app: App):
    """Update the Django application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    app_name = django_app.name
    orig_config = juju.config(app_name)

    request_config = {k: str(v) for k, v in request.param.items()}
    juju.config(app_name, request_config)
    juju.wait(lambda status: jubilant.all_active(status, app_name))

    yield request_config

    # Restore original configuration
    restore_config = {k: str(v) for k, v in orig_config.items() if k in request_config}
    reset_config = [k for k in request_config if orig_config.get(k) is None]
    juju.config(app_name, restore_config, reset=reset_config)