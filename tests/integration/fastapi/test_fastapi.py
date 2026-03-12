# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for FastAPI charm."""

import logging

import jubilant
import requests

from tests.integration.helpers import fetch_container_json_logs, logs_for_logger
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


def test_json_logging(
    fastapi_app: App,
    juju: jubilant.Juju,
):
    """
    arrange: deploy the FastAPI charm with framework_logging_format=json in paas-config.yaml.
    act: make a request to GET /boom (access log + error log with exception).
    assert: container logs contain valid JSON with OTEL fields, trace correlation, and exception info.
    """
    status = juju.status()
    unit = next(iter(status.apps[fastapi_app.name].units.values()))
    model_name = status.model.name
    pod_name = f"{fastapi_app.name}-0"

    requests.get(f"http://{unit.address}:{WORKLOAD_PORT}/boom", timeout=5)

    all_logs = fetch_container_json_logs(pod_name, model_name, "app")

    access_logs = logs_for_logger(all_logs, "uvicorn.access")
    assert access_logs, "No JSON access log lines found in uvicorn.access logger."
    sample = access_logs[0]
    for field in ("timestamp", "severityText", "body", "attributes"):
        assert field in sample, f"Expected OTEL field {field!r} missing: {sample}"
    for attr in ("logger.name", "http.request.method", "url.path", "http.response.status_code"):
        assert attr in sample.get(
            "attributes", {}
        ), f"Expected OTEL attribute {attr!r} missing from access log: {sample}"
    assert "traceId" in sample, f"traceId missing from access log: {sample}"
    assert "spanId" in sample, f"spanId missing from access log: {sample}"

    error_logs = logs_for_logger(all_logs, "uvicorn.error")
    assert error_logs, "No JSON error log lines found in container logs after hitting /boom."
    err = error_logs[-1]
    attrs = err.get("attributes", {})
    assert "exception.type" in attrs, f"exception.type missing from error log: {err}"
    assert (
        attrs.get("exception.message") == "intentional error for log testing"
    ), f"Unexpected exception.message: {attrs.get('exception.message')}"
    assert "exception.stacktrace" in attrs, f"exception.stacktrace missing from error log: {err}"
    assert "traceId" in err, f"traceId missing from error log: {err}"
    assert "spanId" in err, f"spanId missing from error log: {err}"
