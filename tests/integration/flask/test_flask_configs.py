#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm configurations."""

import json
import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

# caused by pytest fixtures
# pylint: disable=too-many-arguments

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8000


@pytest.mark.parametrize(
    "update_config, expected_config",
    [
        pytest.param({"flask-env": "testing"}, {"ENV": "testing"}, id="env"),
        pytest.param(
            {"flask-permanent-session-lifetime": 100},
            {"PERMANENT_SESSION_LIFETIME": 100},
            id="permanent_session_lifetime",
        ),
        pytest.param({"flask-debug": True}, {"DEBUG": True}, id="debug"),
    ],
    indirect=["update_config"],
)
@pytest.mark.usefixtures("update_config")
def test_flask_config(
    flask_app: App,
    juju: jubilant.Juju,
    session_with_retry: requests.Session,
    expected_config: dict,
):
    """
    arrange: build and deploy the flask charm, and change flask related configurations.
    act: query flask configurations from the Flask server.
    assert: the flask configuration should match flask related charm configurations.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        for config_key, config_value in expected_config.items():
            assert (
                session_with_retry.get(
                    f"http://{unit.address}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )


@pytest.mark.parametrize(
    "update_secret_config, expected_config",
    [
        pytest.param(
            {"secret-test": {"bar": "bar", "foo-bar": "foo-bar"}},
            {
                "SECRET_TEST_BAR": "bar",
                "SECRET_TEST_TOKEN": "foo-bar",
                "SECRET_TEST_FOO_BAR": None,
            },
            id="user-secret",
        ),
        pytest.param(
            {"app-secret-key": {"value": "secret-foobar"}},
            {"SECRET_KEY": "secret-foobar"},
            id="secret_key",
        ),
    ],
    indirect=["update_secret_config"],
)
@pytest.mark.usefixtures("update_secret_config")
def test_flask_secret_config(
    flask_app: App,
    juju: jubilant.Juju,
    session_with_retry: requests.Session,
    expected_config: dict,
):
    """
    arrange: build and deploy the flask charm, and change secret configurations.
    act: query secret configuration values from the Flask server.
    assert: mapped entries use their selected names, unmapped entries keep their default
        names, and renamed entries are absent under their default names.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        for config_key, config_value in expected_config.items():
            assert (
                session_with_retry.get(
                    f"http://{unit.address}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )


def _assert_blocked_with_message(juju: jubilant.Juju, app_name: str, expected: str):
    """Wait for the app to be blocked and check the status message mentions ``expected``."""
    status = juju.wait(
        lambda status: jubilant.all_blocked(status, app_name),
        error=lambda status: jubilant.any_error(status, app_name),
        timeout=5 * 60,
    )
    app_status = status.apps[app_name]
    assert expected in app_status.app_status.message
    for unit in app_status.units.values():
        assert expected in unit.workload_status.message


@pytest.mark.parametrize(
    "ungranted_secret_config",
    [
        pytest.param("secret-test", id="user-secret"),
        pytest.param("app-secret-key", id="secret_key"),
    ],
    indirect=True,
)
@pytest.mark.usefixtures("fast_update_status")
def test_flask_secret_config_not_granted(
    flask_app: App,
    juju: jubilant.Juju,
    ungranted_secret_config: tuple[str, str],
):
    """
    arrange: build and deploy the flask charm, and set a secret configuration option to a
        secret that has not been granted to the application.
    act: grant the secret to the application.
    assert: the charm should be blocked (not in error) with a status message mentioning the
        configuration option, and become active once the secret is granted.
    """
    config_option, secret_id = ungranted_secret_config

    _assert_blocked_with_message(juju, flask_app.name, config_option)

    juju.grant_secret(secret_id, flask_app.name)
    juju.wait(
        lambda status: jubilant.all_active(status, flask_app.name),
        error=lambda status: jubilant.any_error(status, flask_app.name),
        timeout=5 * 60,
    )


@pytest.mark.parametrize(
    "empty_secret_config",
    [
        pytest.param("secret-test", id="user-secret"),
        pytest.param("app-secret-key", id="secret_key"),
    ],
    indirect=True,
)
def test_flask_secret_config_empty(
    flask_app: App,
    juju: jubilant.Juju,
    empty_secret_config: str,
):
    """
    arrange: build and deploy the flask charm, and set a secret configuration option to an
        empty string.
    act: none.
    assert: the charm should be blocked (not in error) with a status message mentioning the
        configuration option.
    """
    _assert_blocked_with_message(juju, flask_app.name, empty_secret_config)


@pytest.mark.parametrize(
    "update_config, invalid_configs",
    [
        pytest.param(
            {"flask-permanent-session-lifetime": -1},
            ("permanent-session-lifetime",),
            id="permanent_session_lifetime",
        ),
        pytest.param(
            {"flask-preferred-url-scheme": "TLS"},
            ("preferred-url-scheme",),
            id="preferred_url_scheme",
        ),
    ],
    indirect=["update_config"],
)
@pytest.mark.usefixtures("update_config")
def test_invalid_flask_config(
    flask_app: App, juju: jubilant.Juju, invalid_configs: tuple[str, ...]
):
    """
    arrange: build and deploy the flask charm, and change flask related configurations
        to certain invalid values.
    act: none.
    assert: flask charm should enter the blocked status and the status message should show
        invalid configuration options.
    """
    status = juju.status()
    app_status = status.apps[flask_app.name]
    assert app_status.is_blocked
    for invalid_config in invalid_configs:
        assert invalid_config in app_status.app_status.message
    for unit in app_status.units.values():
        assert unit.is_blocked
        for invalid_config in invalid_configs:
            assert invalid_config in unit.workload_status.message


@pytest.mark.parametrize(
    "update_config, expected_config",
    [
        pytest.param(
            {"foo-str": "testing"},
            {"MAPPED_STRING": "testing", "FOO_STR": None},
            id="str",
        ),
        pytest.param({"foo-int": 128}, {"FOO_INT": 128}, id="int"),
        pytest.param({"foo-bool": True}, {"FOO_BOOL": True}, id="bool"),
        pytest.param({"foo-dict": json.dumps({"a": 1})}, {"FOO_DICT": {"a": 1}}, id="dict"),
        pytest.param({"application-root": "/foo"}, {"APPLICATION_ROOT": "/"}, id="builtin"),
    ],
    indirect=["update_config"],
)
@pytest.mark.usefixtures("update_config")
def test_app_config(
    flask_app: App,
    juju: jubilant.Juju,
    session_with_retry: requests.Session,
    expected_config: dict[str, str | int | bool | dict[str, int] | None],
):
    """
    arrange: build and deploy the flask charm, and change Flask app configurations.
    act: none.
    assert: Flask receives configuration values, including the renamed string option
        without its default environment variable name.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        for config_key, config_value in expected_config.items():
            assert (
                session_with_retry.get(
                    f"http://{unit.address}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )
