# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for FastAPI charm integration tests."""

import jubilant
import pytest

from tests.integration.types import App


@pytest.fixture(scope="function")
def update_config(juju: jubilant.Juju, request: pytest.FixtureRequest, fastapi_app: App):
    """Update the FastAPI application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    app_name = fastapi_app.name
    orig_config = juju.config(app_name)

    request_config = {k: str(v) for k, v in request.param.items()}
    juju.config(app_name, request_config)
    juju.wait(
        lambda status: status.apps[app_name].is_active or status.apps[app_name].is_blocked,
        successes=5,
        delay=10,
    )

    yield request_config

    # Restore original configuration
    restore_config = {k: str(v) for k, v in orig_config.items() if k in request_config}
    reset_config = [k for k in request_config if orig_config.get(k) is None]
    juju.config(app_name, restore_config, reset=reset_config)
