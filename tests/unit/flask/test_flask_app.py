# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm unit tests for the flask_app module."""

# this is a unit test file
# pylint: disable=protected-access

import json
import pathlib
import typing

import pytest

from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm._gunicorn.wsgi_app import WsgiApp
from paas_charm.charm_state import CharmState


@pytest.mark.parametrize(
    "flask_config,user_defined_config",
    [
        pytest.param({"env": "test"}, {}, id="env"),
        pytest.param({"permanent_session_lifetime": 1}, {}, id="permanent_session_lifetime"),
        pytest.param({"debug": True}, {}, id="debug"),
        pytest.param({"application_root": "/"}, {"application_root": "/foo"}, id="duplicate"),
        pytest.param(
            {"application_root": "/"},
            {"secret_test": {"foo": "foo", "foo-bar": "foobar"}},
            id="secrets",
        ),
    ],
)
def test_flask_env(
    flask_config: dict,
    user_defined_config: dict,
    database_migration_mock,
    flask_container_mock,
    webserver,
):
    """
    arrange: create the Flask app object with a controlled charm state.
    act: none.
    assert: flask_environment generated by the Flask app object should be acceptable by Flask app.
    """
    charm_state = CharmState(
        framework="flask",
        secret_key="foobar",
        is_secret_storage_ready=True,
        framework_config=flask_config,
        user_defined_config=user_defined_config,
    )
    workload_config = create_workload_config(
        framework_name="flask", unit_name="flask/0", state_dir=pathlib.Path("/tmp/flask/state")
    )
    flask_app = WsgiApp(
        container=flask_container_mock,
        charm_state=charm_state,
        workload_config=workload_config,
        webserver=webserver,
        database_migration=database_migration_mock,
    )
    env = flask_app.gen_environment()
    assert env["FLASK_SECRET_KEY"] == "foobar"
    del env["FLASK_SECRET_KEY"]
    expected_env = {}
    for config_key, config_value in user_defined_config.items():
        if isinstance(config_value, dict):
            for secret_key, secret_value in config_value.items():
                expected_env[
                    f"FLASK_{config_key.replace('-', '_').upper()}_{secret_key.replace('-', '_').upper()}"
                ] = secret_value
        else:
            expected_env[f"FLASK_{config_key.replace('-', '_').upper()}"] = (
                config_value if isinstance(config_value, str) else json.dumps(config_value)
            )
    expected_env.update(
        {
            f"FLASK_{k.upper()}": v if isinstance(v, str) else json.dumps(v)
            for k, v in flask_config.items()
        }
    )
    assert env == expected_env


HTTP_PROXY_TEST_PARAMS = [
    pytest.param({}, {}, id="no_env"),
    pytest.param({"JUJU_CHARM_NO_PROXY": "127.0.0.1"}, {"no_proxy": "127.0.0.1"}, id="no_proxy"),
    pytest.param(
        {"JUJU_CHARM_HTTP_PROXY": "http://proxy.test"},
        {"http_proxy": "http://proxy.test"},
        id="http_proxy",
    ),
    pytest.param(
        {"JUJU_CHARM_HTTPS_PROXY": "http://proxy.test"},
        {"https_proxy": "http://proxy.test"},
        id="https_proxy",
    ),
    pytest.param(
        {
            "JUJU_CHARM_HTTP_PROXY": "http://proxy.test",
            "JUJU_CHARM_HTTPS_PROXY": "http://proxy.test",
        },
        {"http_proxy": "http://proxy.test", "https_proxy": "http://proxy.test"},
        id="http_https_proxy",
    ),
]


@pytest.mark.parametrize(
    "set_env, expected",
    HTTP_PROXY_TEST_PARAMS,
)
def test_http_proxy(
    set_env: typing.Dict[str, str],
    expected: typing.Dict[str, str],
    monkeypatch,
    database_migration_mock,
    flask_container_mock,
    webserver,
):
    """
    arrange: set juju charm http proxy related environment variables.
    act: generate a flask environment.
    assert: flask_environment generated should contain proper proxy environment variables.
    """
    for set_env_name, set_env_value in set_env.items():
        monkeypatch.setenv(set_env_name, set_env_value)
    charm_state = CharmState(
        framework="flask",
        secret_key="foobar",
        is_secret_storage_ready=True,
    )
    workload_config = create_workload_config(
        framework_name="flask", unit_name="flask/0", state_dir=pathlib.Path("/tmp/flask/state")
    )
    flask_app = WsgiApp(
        container=flask_container_mock,
        charm_state=charm_state,
        workload_config=workload_config,
        webserver=webserver,
        database_migration=database_migration_mock,
    )
    env = flask_app.gen_environment()
    expected_env: typing.Dict[str, typing.Optional[str]] = {
        "http_proxy": None,
        "https_proxy": None,
        "no_proxy": None,
    }
    expected_env.update(expected)
    for env_name, env_value in expected_env.items():
        assert env.get(env_name) == env.get(env_name.upper()) == env_value
