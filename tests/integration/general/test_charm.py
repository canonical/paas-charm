#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12-factor charms."""
import logging
import typing

import pytest
import requests

# caused by pytest fixtures
# pylint: disable=too-many-arguments

logger = logging.getLogger(__name__)

WORKLOAD_PORT = 8000


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
        ("expressjs_app", 8080),
    ],
)
async def test_charm_is_up(
    app_fixture: str,
    port: int,
    get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
    request: pytest.FixtureRequest,
):
    """
    arrange: build and deploy the flask charm.
    act: send a request to the flask application managed by the flask charm.
    assert: the flask application should return a correct response.
    """
    app = request.getfixturevalue(app_fixture)
    for unit_ip in await get_unit_ips(app.name):
        response = requests.get(f"http://{unit_ip}:{port}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text

# @pytest.mark.parametrize(
#     "app_fixture, port",
#     [
#         ("flask_app", 8000),
#         ("django_app", 8000),
#         ("fastapi_app", 8080),
#         ("go_app", 8080),
#         ("expressjs_app", 8080),
#     ],
# )
# async def test_default_secret_key(
#     app_fixture: str,
#     port: int,
#     get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
#     request: pytest.FixtureRequest,
# ):
#     """
#     arrange: build and deploy the flask charm.
#     act: query flask secret key from the Flask server.
#     assert: flask should have a default and secure secret configured.
#     """
#     app = request.getfixturevalue(app_fixture)
#     secret_keys = [
#         requests.get(f"http://{unit_ip}:{port}/config/SECRET_KEY", timeout=10).json()
#         for unit_ip in await get_unit_ips(app.name)
#     ]
#     assert len(set(secret_keys)) == 1
#     assert len(secret_keys[0]) > 10


# @pytest.mark.parametrize(
#     "app_fixture, port",
#     [
#         ("flask_app", 8000),
#         ("django_app", 8000),
#         ("fastapi_app", 8080),
#         ("go_app", 8080),
#         ("expressjs_app", 8080),
#     ],
# )
# async def test_port_without_ingress(
#     app_fixture: str,
#     port: int,
#     model: juju.model.Model,
#     request: pytest.FixtureRequest,
# ):
#     """
#     arrange: build and deploy the flask charm without ingress. Get the service ip
#         address.
#     act: request env variables through the service ip address.
#     assert: the request should success and the env variable FLASK_BASE_URL
#         should point to the service.
#     """
#     app = request.getfixturevalue(app_fixture)
#     service_hostname = f"{app.name}.{model.name}"
#     action = await app.units[0].run(f"/usr/bin/getent hosts {service_hostname}")
#     result = await action.wait()
#     assert result.status == "completed"
#     assert result.results["return-code"] == 0
#     service_ip = result.results["stdout"].split()[0]

#     response = requests.get(f"http://{service_ip}:{port}/env", timeout=30)

#     assert response.status_code == 200
#     env_vars = response.json()
#     assert env_vars["FLASK_BASE_URL"] == f"http://{service_hostname}:{WORKLOAD_PORT}"

# @pytest.mark.parametrize(
#     "app_fixture, port",
#     [
#         ("flask_app", 8000),
#         ("django_app", 8000),
#         ("fastapi_app", 8080),
#         ("go_app", 8080),
#         ("expressjs_app", 8080),
#     ],
# )
# async def test_with_ingress(
#     app_fixture: str,
#     port: int,
#     request: pytest.FixtureRequest,
#     ops_test: OpsTest,
#     model: juju.model.Model,
#     traefik_app,  # pylint: disable=unused-argument
#     traefik_app_name: str,
#     external_hostname: str,
#     get_unit_ips: typing.Callable[[str], typing.Awaitable[tuple[str, ...]]],
# ):
#     """
#     arrange: build and deploy the flask charm, and deploy the ingress.
#     act: relate the ingress charm with the Flask charm.
#     assert: requesting the charm through traefik should return a correct response,
#          and the BASE_URL config should be correctly set (FLASK_BASE_URL env variable).
#     """
#     app = request.getfixturevalue(app_fixture)
#     await model.add_relation(app.name, traefik_app_name)
#     # mypy doesn't see that ActiveStatus has a name
#     await model.wait_for_idle(status=ops.ActiveStatus.name)  # type: ignore

#     traefik_ip = (await get_unit_ips(traefik_app_name))[0]
#     response = requests.get(
#         f"http://{traefik_ip}/config/BASE_URL",
#         headers={"Host": f"{ops_test.model_name}-{app.name}.{external_hostname}"},
#         timeout=5,
#     )
#     assert response.status_code == 200
#     assert response.json() == f"http://{ops_test.model_name}-{app.name}.{external_hostname}/"