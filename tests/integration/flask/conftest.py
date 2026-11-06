# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import os
import pathlib

import jubilant
import pytest

from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/flask/charm")


@pytest.fixture(scope="function")
def update_config(juju: jubilant.Juju, request: pytest.FixtureRequest, flask_app: App):
    """Update the flask application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    app_name = flask_app.name
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


@pytest.fixture(scope="function")
def update_secret_config(juju: jubilant.Juju, request: pytest.FixtureRequest, flask_app: App):
    """Update a secret flask application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    app_name = flask_app.name
    orig_config = juju.config(app_name)
    request_config = {}
    secret_ids = []

    for secret_config_option, secret_value in request.param.items():
        secret_id = juju.add_secret(secret_config_option, secret_value)

        juju.grant_secret(secret_id, app_name)
        request_config[secret_config_option] = secret_id
        secret_ids.append(secret_id)

    juju.config(app_name, request_config)
    juju.wait(lambda status: status.apps[app_name].is_active, successes=5, delay=10)

    yield request_config

    # Restore original configuration
    restore_config = {k: str(v) for k, v in orig_config.items() if k in request_config}
    reset_config = [k for k in request_config if orig_config.get(k) is None]
    juju.config(app_name, restore_config, reset=reset_config)

    for secret_id in secret_ids:
        juju.remove_secret(secret_id)


@pytest.fixture(scope="function")
def fast_update_status(juju: jubilant.Juju):
    """Temporarily shorten the update-status hook interval of the model."""
    orig_interval = juju.model_config()["update-status-hook-interval"]
    juju.model_config({"update-status-hook-interval": "10s"})
    yield
    juju.model_config({"update-status-hook-interval": orig_interval})


@pytest.fixture(scope="function")
def ungranted_secret_config(juju: jubilant.Juju, request: pytest.FixtureRequest, flask_app: App):
    """Set a secret configuration option to a secret the application has not been granted.

    This fixture must be parameterized with a single secret configuration option name.
    Yields the configuration option name and the secret ID.
    """
    app_name = flask_app.name
    config_option = request.param
    secret_id = juju.add_secret(f"{config_option}-ungranted", {"value": "foobar"})
    juju.config(app_name, {config_option: secret_id})

    yield config_option, secret_id

    juju.config(app_name, reset=[config_option])
    juju.remove_secret(secret_id)
    juju.wait(lambda status: status.apps[app_name].is_active, successes=5, delay=10)


@pytest.fixture(scope="function")
def empty_secret_config(juju: jubilant.Juju, request: pytest.FixtureRequest, flask_app: App):
    """Set a secret configuration option to an empty string.

    This fixture must be parameterized with a single secret configuration option name.
    Yields the configuration option name.
    """
    app_name = flask_app.name
    config_option = request.param
    juju.config(app_name, {config_option: ""})

    yield config_option

    juju.config(app_name, reset=[config_option])
    juju.wait(lambda status: status.apps[app_name].is_active, successes=5, delay=10)
