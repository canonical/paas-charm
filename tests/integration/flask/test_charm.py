#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm."""

import json
import logging
import typing

import juju
import ops
import pytest
import requests
from juju.application import Application
from pytest_operator.plugin import OpsTest

# caused by pytest fixtures
# pylint: disable=too-many-arguments

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8000


async def test_flask_is_up(
    flask_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the flask charm.
    act: send a request to the flask application managed by the flask charm.
    assert: the flask application should return a correct response.
    """
    for unit_ip in await get_unit_ips(flask_app.name):
        response = requests.get(f"http://{unit_ip}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


@pytest.mark.parametrize(
    "update_config, timeout",
    [
        pytest.param({"webserver-timeout": 7}, 7, id="timeout=7"),
        pytest.param({"webserver-timeout": 5}, 5, id="timeout=5"),
        pytest.param({"webserver-timeout": 3}, 3, id="timeout=3"),
    ],
    indirect=["update_config"],
)
@pytest.mark.usefixtures("update_config")
async def test_flask_webserver_timeout(
    flask_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
    timeout: int,
):
    """
    arrange: build and deploy the flask charm, and change the gunicorn timeout configuration.
    act: send long-running requests to the flask application managed by the flask charm.
    assert: the gunicorn should restart the worker if the request duration exceeds the timeout.
    """
    safety_timeout = timeout + 3
    for unit_ip in await get_unit_ips(flask_app.name):
        assert requests.get(
            f"http://{unit_ip}:{WORKLOAD_PORT}/sleep?duration={timeout - 1}",
            timeout=safety_timeout,
        ).ok
        assert not requests.get(
            f"http://{unit_ip}:{WORKLOAD_PORT}/sleep?duration={timeout + 1}",
            timeout=safety_timeout,
        ).ok


async def test_default_secret_key(
    flask_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the flask charm.
    act: query flask secret key from the Flask server.
    assert: flask should have a default and secure secret configured.
    """
    secret_keys = [
        requests.get(f"http://{unit_ip}:{WORKLOAD_PORT}/config/SECRET_KEY", timeout=10).json()
        for unit_ip in await get_unit_ips(flask_app.name)
    ]
    assert len(set(secret_keys)) == 1
    assert len(secret_keys[0]) > 10


@pytest.mark.parametrize(
    "update_config, excepted_config",
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
async def test_flask_config(
    flask_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
    excepted_config: dict,
):
    """
    arrange: build and deploy the flask charm, and change flask related configurations.
    act: query flask configurations from the Flask server.
    assert: the flask configuration should match flask related charm configurations.
    """
    for unit_ip in await get_unit_ips(flask_app.name):
        for config_key, config_value in excepted_config.items():
            assert (
                requests.get(
                    f"http://{unit_ip}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )


@pytest.mark.parametrize(
    "update_secret_config, excepted_config",
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
async def test_flask_secret_config(
    flask_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
    excepted_config: dict,
):
    """
    arrange: build and deploy the flask charm, and change secret configurations.
    act: query flask environment variables from the Flask server.
    assert: the flask environment variables should match secret configuration values.
    """
    for unit_ip in await get_unit_ips(flask_app.name):
        for config_key, config_value in excepted_config.items():
            assert (
                requests.get(
                    f"http://{unit_ip}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
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
async def test_invalid_flask_config(flask_app: Application, invalid_configs: tuple[str, ...]):
    """
    arrange: build and deploy the flask charm, and change flask related configurations
        to certain invalid values.
    act: none.
    assert: flask charm should enter the blocked status and the status message should show
        invalid configuration options.
    """
    assert flask_app.status == "blocked"
    for invalid_config in invalid_configs:
        assert invalid_config in flask_app.status_message
    for unit in flask_app.units:
        assert unit.workload_status == "blocked"
        for invalid_config in invalid_configs:
            assert invalid_config in unit.workload_status_message


@pytest.mark.parametrize(
    "update_config, excepted_config",
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
async def test_app_config(
    flask_app: Application,
    excepted_config: dict[str, str | int | bool],
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the flask charm, and change Flask app configurations.
    act: none.
    assert: Flask application should receive the application configuration correctly.
    """
    for unit_ip in await get_unit_ips(flask_app.name):
        for config_key, config_value in excepted_config.items():
            assert (
                requests.get(
                    f"http://{unit_ip}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )


async def test_rotate_secret_key(
    model: juju.model.Model,
    flask_app: Application,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the flask charm.
    act: run rotate-secret-key action on the leader unit.
    assert: Flask applications on every unit should have a new secret key configured.
    """
    unit_ips = await get_unit_ips(flask_app.name)
    secret_key = requests.get(
        f"http://{unit_ips[0]}:{WORKLOAD_PORT}/config/SECRET_KEY", timeout=10
    ).json()
    leader_unit = [u for u in flask_app.units if await u.is_leader_from_status()][0]
    action = await leader_unit.run_action("rotate-secret-key")
    await action.wait()
    assert action.results["status"] == "success"
    await model.wait_for_idle(status=ops.ActiveStatus.name)  # type: ignore
    for unit_ip in unit_ips:
        new_secret_key = requests.get(
            f"http://{unit_ip}:{WORKLOAD_PORT}/config/SECRET_KEY", timeout=10
        ).json()
        assert len(new_secret_key) > 10
        assert new_secret_key != secret_key


async def test_port_without_ingress(
    model: juju.model.Model,
    flask_app: Application,
):
    """
    arrange: build and deploy the flask charm without ingress. Get the service ip
        address.
    act: request env variables through the service ip address.
    assert: the request should success and the env variable FLASK_BASE_URL
        should point to the service.
    """
    service_hostname = f"{flask_app.name}.{model.name}"
    action = await flask_app.units[0].run(f"/usr/bin/getent hosts {service_hostname}")
    result = await action.wait()
    assert result.status == "completed"
    assert result.results["return-code"] == 0
    service_ip = result.results["stdout"].split()[0]

    response = requests.get(f"http://{service_ip}:{WORKLOAD_PORT}/env", timeout=30)

    assert response.status_code == 200
    env_vars = response.json()
    assert env_vars["FLASK_BASE_URL"] == f"http://{service_hostname}:{WORKLOAD_PORT}"


async def test_with_ingress(
    ops_test: OpsTest,
    model: juju.model.Model,
    flask_app: Application,
    traefik_app,  # pylint: disable=unused-argument
    traefik_app_name: str,
    external_hostname: str,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
):
    """
    arrange: build and deploy the flask charm, and deploy the ingress.
    act: relate the ingress charm with the Flask charm.
    assert: requesting the charm through traefik should return a correct response,
         and the BASE_URL config should be correctly set (FLASK_BASE_URL env variable).
    """
    await model.add_relation(flask_app.name, traefik_app_name)
    # mypy doesn't see that ActiveStatus has a name
    await model.wait_for_idle(status=ops.ActiveStatus.name)  # type: ignore

    traefik_ip = (await get_unit_ips(traefik_app_name))[0]
    response = requests.get(
        f"http://{traefik_ip}/config/BASE_URL",
        headers={"Host": f"{ops_test.model_name}-{flask_app.name}.{external_hostname}"},
        timeout=5,
    )
    assert response.status_code == 200
    assert response.json() == f"http://{ops_test.model_name}-{flask_app.name}.{external_hostname}/"
