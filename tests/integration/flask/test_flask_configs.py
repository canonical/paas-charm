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
        pytest.param({"flask-secret-key": "foobar"}, {"SECRET_KEY": "foobar"}, id="secret_key"),
    ],
    indirect=["update_config"],
)
@pytest.mark.usefixtures("update_config")
def test_flask_config(
    flask_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
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
                http.get(
                    f"http://{unit.address}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )


@pytest.mark.parametrize(
    "update_secret_config, expected_config",
    [
        pytest.param(
            {"secret-test": {"bar": "bar", "foo-bar": "foo-bar"}},
            {"SECRET_TEST_BAR": "bar", "SECRET_TEST_FOO_BAR": "foo-bar"},
            id="user-secret",
        ),
        pytest.param(
            {"flask-secret-key-id": {"value": "secret-foobar"}},
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
    http: requests.Session,
    expected_config: dict,
):
    """
    arrange: build and deploy the flask charm, and change secret configurations.
    act: query flask environment variables from the Flask server.
    assert: the flask environment variables should match secret configuration values.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        for config_key, config_value in expected_config.items():
            assert (
                http.get(
                    f"http://{unit.address}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )


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
        pytest.param({"foo-str": "testing"}, {"FOO_STR": "testing"}, id="str"),
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
    http: requests.Session,
    expected_config: dict[str, str | int | bool],
):
    """
    arrange: build and deploy the flask charm, and change Flask app configurations.
    act: none.
    assert: Flask application should receive the application configuration correctly.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        for config_key, config_value in expected_config.items():
            assert (
                http.get(
                    f"http://{unit.address}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )
