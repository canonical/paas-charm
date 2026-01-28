#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm."""

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


def test_flask_is_up(
    flask_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: send a request to the flask application managed by the flask charm.
    assert: the flask application should return a correct response.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        response = http.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)
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
def test_flask_webserver_timeout(
    flask_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
    timeout: int,
):
    """
    arrange: build and deploy the flask charm, and change the gunicorn timeout configuration.
    act: send long-running requests to the flask application managed by the flask charm.
    assert: the gunicorn should restart the worker if the request duration exceeds the timeout.
    """
    safety_timeout = timeout + 3
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        assert http.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/sleep?duration={timeout - 1}",
            timeout=safety_timeout,
        ).ok
        assert not http.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/sleep?duration={timeout + 1}",
            timeout=safety_timeout,
        ).ok


def test_default_secret_key(
    flask_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: query flask secret key from the Flask server.
    assert: flask should have a default and secure secret configured.
    """
    status = juju.status()
    secret_keys = [
        http.get(f"http://{unit.address}:{WORKLOAD_PORT}/config/SECRET_KEY", timeout=10).json()
        for unit in status.apps[flask_app.name].units.values()
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
def test_flask_config(
    flask_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
    excepted_config: dict,
):
    """
    arrange: build and deploy the flask charm, and change flask related configurations.
    act: query flask configurations from the Flask server.
    assert: the flask configuration should match flask related charm configurations.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        for config_key, config_value in excepted_config.items():
            assert (
                http.get(
                    f"http://{unit.address}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
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
def test_flask_secret_config(
    flask_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
    excepted_config: dict,
):
    """
    arrange: build and deploy the flask charm, and change secret configurations.
    act: query flask environment variables from the Flask server.
    assert: the flask environment variables should match secret configuration values.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        for config_key, config_value in excepted_config.items():
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
def test_app_config(
    flask_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
    excepted_config: dict[str, str | int | bool],
):
    """
    arrange: build and deploy the flask charm, and change Flask app configurations.
    act: none.
    assert: Flask application should receive the application configuration correctly.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        for config_key, config_value in excepted_config.items():
            assert (
                http.get(
                    f"http://{unit.address}:{WORKLOAD_PORT}/config/{config_key}", timeout=10
                ).json()
                == config_value
            )


def test_rotate_secret_key(
    juju: jubilant.Juju,
    flask_app: App,
    http: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: run rotate-secret-key action on the leader unit.
    assert: Flask applications on every unit should have a new secret key configured.
    """
    status = juju.status()
    units = list(status.apps[flask_app.name].units.values())
    secret_key = http.get(
        f"http://{units[0].address}:{WORKLOAD_PORT}/config/SECRET_KEY", timeout=10
    ).json()

    # Find leader unit
    leader_unit = None
    for unit_name in status.apps[flask_app.name].units.keys():
        if status.apps[flask_app.name].units[unit_name].leader:
            leader_unit = unit_name
            break
    assert leader_unit is not None
    task = juju.run(leader_unit, "rotate-secret-key")
    assert task.results["status"] == "success"
    juju.wait(lambda status: status.apps[flask_app.name].is_active)

    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        new_secret_key = http.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/config/SECRET_KEY", timeout=10
        ).json()
        assert len(new_secret_key) > 10
        assert new_secret_key != secret_key


def test_port_without_ingress(
    juju: jubilant.Juju,
    flask_app: App,
    http: requests.Session,
):
    """
    arrange: build and deploy the flask charm without ingress. Get the service ip
        address.
    act: request env variables through the service ip address.
    assert: the request should success and the env variable FLASK_BASE_URL
        should point to the service.
    """
    status = juju.status()
    model_name = status.model.name
    service_hostname = f"{flask_app.name}.{model_name}"
    unit_name = list(status.apps[flask_app.name].units.keys())[0]

    task = juju.run(unit_name, f"/usr/bin/getent hosts {service_hostname}")
    assert task.results["return-code"] == 0
    service_ip = task.results["stdout"].split()[0]

    response = http.get(f"http://{service_ip}:{WORKLOAD_PORT}/env", timeout=30)

    assert response.status_code == 200
    env_vars = response.json()
    assert env_vars["FLASK_BASE_URL"] == f"http://{service_hostname}:{WORKLOAD_PORT}"


def test_with_ingress(
    juju: jubilant.Juju,
    flask_app: App,
    traefik_app: App,
    traefik_app_name: str,
    external_hostname: str,
    http: requests.Session,
):
    """
    arrange: build and deploy the flask charm, and deploy the ingress.
    act: relate the ingress charm with the Flask charm.
    assert: requesting the charm through traefik should return a correct response,
         and the BASE_URL config should be correctly set (FLASK_BASE_URL env variable).
    """
    try:
        juju.integrate(flask_app.name, traefik_app_name)
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    juju.wait(lambda status: jubilant.all_active(status, flask_app.name, traefik_app_name))

    status = juju.status()
    model_name = status.model.name
    traefik_unit = list(status.apps[traefik_app_name].units.values())[0]
    traefik_ip = traefik_unit.address

    response = http.get(
        f"http://{traefik_ip}/config/BASE_URL",
        headers={"Host": f"{model_name}-{flask_app.name}.{external_hostname}"},
        timeout=5,
    )
    assert response.status_code == 200
    assert response.json() == f"http://{model_name}-{flask_app.name}.{external_hostname}/"


def test_app_peer_address(
    juju: jubilant.Juju,
    flask_app: App,
    http: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: add a unit and request env variables through the unit IP addresses.
    assert: the peer address must be present in the units' env.
    """
    # Add a unit
    juju.add_unit(flask_app.name)
    juju.wait(lambda status: status.apps[flask_app.name].is_active)

    status = juju.status()
    model_name = status.model.name

    actual_result = set()
    for unit in status.apps[flask_app.name].units.values():
        response = http.get(f"http://{unit.address}:{WORKLOAD_PORT}/env", timeout=30)
        assert response.status_code == 200
        env_vars = response.json()
        assert "FLASK_PEER_FQDNS" in env_vars
        actual_result.add(env_vars["FLASK_PEER_FQDNS"])

    expected_result = set()
    for unit_name in status.apps[flask_app.name].units.keys():
        # <unit-name>.<app-name>-endpoints.<model-name>.svc.cluster.local
        expected_result.add(
            f"{unit_name.replace('/', '-')}.{flask_app.name}-endpoints.{model_name}.svc.cluster.local"
        )
    assert actual_result == expected_result

    # Scale back to 1 unit
    juju.remove_unit(flask_app.name, num_units=1)
    juju.wait(lambda status: status.apps[flask_app.name].is_active)

    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        response = http.get(f"http://{unit.address}:{WORKLOAD_PORT}/env", timeout=30)
        assert response.status_code == 200
        env_vars = response.json()
        assert "FLASK_PEER_FQDNS" not in env_vars
