# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for FastAPI charm."""

import json
import logging
import subprocess

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)
WORKLOAD_PORT = 8080


def test_fastapi_is_up(fastapi_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the fastapi charm.
    act: send a request to the fastapi application managed by the fastapi charm.
    assert: the fastapi application should return a correct response.
    """
    status = juju.status()
    for unit in status.apps[fastapi_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)
        assert response.status_code == 200
        assert "Hello, World!" in response.text


def test_user_defined_config(fastapi_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the fastapi charm. Set the config user-defined-config to a new value.
    act: call the endpoint to get the value of the env variable related to the config.
    assert: the value of the env variable and the config should match.
    """
    juju.config(fastapi_app.name, {"user-defined-config": "newvalue"})
    juju.wait(lambda status: jubilant.all_active(status, fastapi_app.name, "postgresql-k8s"))

    status = juju.status()
    for unit in status.apps[fastapi_app.name].units.values():
        assert unit.is_active, f"Unit {unit.name} is not active"
        response = requests.get(
            f"http://{unit.address}:{WORKLOAD_PORT}/env/user-defined-config", timeout=5
        )
        assert response.status_code == 200
        assert "newvalue" in response.text


def test_migration(fastapi_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the fastapi charm with postgresql integration.
    act: send a request to an endpoint that checks the table created by the micration script.
    assert: the fastapi application should return a correct response.
    """
    status = juju.status()
    for unit in status.apps[fastapi_app.name].units.values():
        response = requests.get(f"http://{unit.address}:{WORKLOAD_PORT}/table/users", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" in response.text


@pytest.mark.parametrize("update_config", [{"framework_logging_format": "json"}], indirect=True)
def test_json_logging_format(
    fastapi_app: App,
    juju: jubilant.Juju,
    update_config: dict,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the FastAPI charm and set framework_logging_format=json.
    act:     make several GET / requests to generate access logs.
    assert:  the container stdout contains valid JSON log lines with ECS fields.
    """
    status = juju.status()
    unit = next(iter(status.apps[fastapi_app.name].units.values()))

    for _ in range(3):
        requests.get(f"http://{unit.address}:{WORKLOAD_PORT}", timeout=5)

    model_name = status.model.name
    pod_name = f"{fastapi_app.name}-0"
    result = subprocess.run(
        ["kubectl", "logs", pod_name, "-c", "app", "-n", model_name],
        capture_output=True,
        text=True,
        check=False,
    )
    raw_logs = result.stdout or result.stderr

    json_lines = []
    for line in raw_logs.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                json_lines.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    access_logs = [log for log in json_lines if log.get("log.logger") == "uvicorn.access"]
    assert access_logs, (
        "No JSON access log lines found in container logs.\n"
        "Raw output (last 20 lines):\n" + "\n".join(raw_logs.splitlines()[-20:])
    )

    sample = access_logs[0]
    for field in (
        "@timestamp",
        "log.level",
        "log.logger",
        "message",
        "http.request.method",
        "url.path",
    ):
        assert (
            field in sample
        ), f"Expected ECS field '{field}' missing from JSON access log: {sample}"
