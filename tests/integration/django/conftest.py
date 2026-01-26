# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for Django charm integration tests."""

import os
import pathlib

import jubilant
import pytest

from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    """Change working directory to Django charm."""
    return os.chdir(PROJECT_ROOT / "examples/django/charm")


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
