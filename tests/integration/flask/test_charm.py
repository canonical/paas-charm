#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm."""

import logging
from functools import wraps
from time import sleep

import jubilant
import pytest
import requests

from tests.integration.types import App

# caused by pytest fixtures
# pylint: disable=too-many-arguments

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8000


def retry_on_assert(max_attempts=5, delay=10):
    """Decorator to retry function if assertion fails."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except AssertionError as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        sleep(delay)
            if last_error:
                raise last_error

        return wrapper

    return decorator


def test_flask_is_up(
    flask_app: App,
    juju: jubilant.Juju,
    session_with_retry: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: send a request to the flask application managed by the flask charm.
    assert: the flask application should return a correct response.
    """
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        response = session_with_retry.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)
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
    session_with_retry: requests.Session,
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
        assert session_with_retry.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/sleep?duration={timeout - 1}",
            timeout=safety_timeout,
        ).ok
        assert not session_with_retry.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/sleep?duration={timeout + 1}",
            timeout=safety_timeout,
        ).ok


def test_default_secret_key(
    flask_app: App,
    juju: jubilant.Juju,
    session_with_retry: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: query flask secret key from the Flask server.
    assert: flask should have a default and secure secret configured.
    """
    status = juju.status()
    secret_keys = [
        session_with_retry.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/config/SECRET_KEY", timeout=10
        ).json()
        for unit in status.apps[flask_app.name].units.values()
    ]
    assert len(set(secret_keys)) == 1
    assert len(secret_keys[0]) > 10


def test_rotate_secret_key(
    juju: jubilant.Juju,
    flask_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: run rotate-secret-key action on the leader unit.
    assert: Flask applications on every unit should have a new secret key configured.
    """
    status = juju.status()
    units = list(status.apps[flask_app.name].units.values())
    secret_key = session_with_retry.get(
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
        new_secret_key = session_with_retry.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/config/SECRET_KEY", timeout=10
        ).json()
        assert len(new_secret_key) > 10
        assert new_secret_key != secret_key


def test_port_without_ingress(
    juju: jubilant.Juju,
    flask_app: App,
    session_with_retry: requests.Session,
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

    task = juju.exec(command=f"/usr/bin/getent hosts {service_hostname}", unit=unit_name)
    assert task.return_code == 0
    service_ip = task.stdout.split()[0]

    response = session_with_retry.get(f"http://{service_ip}:{WORKLOAD_PORT}/env", timeout=30)

    assert response.status_code == 200
    env_vars = response.json()
    assert env_vars["FLASK_BASE_URL"] == f"http://{service_hostname}:{WORKLOAD_PORT}"


def test_with_ingress(
    juju: jubilant.Juju,
    flask_app: App,
    traefik_app: App,
    traefik_app_name: str,
    external_hostname: str,
    session_with_retry: requests.Session,
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
    juju.wait(
        lambda status: jubilant.all_active(status, flask_app.name, traefik_app_name), delay=5
    )

    status = juju.status()
    model_name = status.model.name
    traefik_unit = list(status.apps[traefik_app_name].units.values())[0]
    traefik_ip = traefik_unit.address

    url = f"http://{traefik_ip}/config/BASE_URL"
    hostname = f"{model_name}-{flask_app.name}.{external_hostname}"
    logger.info("checking endpoint: %s with hostname %s", url, hostname)
    response = session_with_retry.get(
        url,
        headers={"Host": hostname},
        timeout=5,
    )
    assert response.status_code == 200
    assert response.json() == f"http://{model_name}-{flask_app.name}.{external_hostname}/"


def test_app_peer_address(
    juju: jubilant.Juju,
    flask_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: add a unit and request env variables through the unit IP addresses.
    assert: the peer address must be present in the units' env.
    """
    # Add a unit
    juju.add_unit(flask_app.name)
    juju.wait(lambda status: status.apps[flask_app.name].is_active, successes=5, delay=5)

    status = juju.status()
    model_name = status.model.name

    @retry_on_assert(max_attempts=5, delay=10)
    def check_peer_fqdns(unit, actual_result: set, is_in: bool = True):
        response = session_with_retry.get(f"http://{unit.address}:{WORKLOAD_PORT}/env", timeout=30)
        assert response.status_code == 200
        env_vars = response.json()
        if is_in:
            assert "FLASK_PEER_FQDNS" in env_vars
            actual_result.add(env_vars["FLASK_PEER_FQDNS"])
        else:
            assert "FLASK_PEER_FQDNS" not in env_vars

    actual_result = set()
    for unit in status.apps[flask_app.name].units.values():
        check_peer_fqdns(unit, actual_result)

    expected_result = set()
    for unit_name in status.apps[flask_app.name].units.keys():
        # <unit-name>.<app-name>-endpoints.<model-name>.svc.cluster.local
        expected_result.add(
            f"{unit_name.replace('/', '-')}.{flask_app.name}-endpoints.{model_name}.svc.cluster.local"
        )
    assert actual_result == expected_result

    # Scale back to 1 unit
    juju.remove_unit(flask_app.name, num_units=1)
    juju.wait(lambda status: status.apps[flask_app.name].is_active, delay=5)
    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        check_peer_fqdns(unit, actual_result, is_in=False)
