# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Tracing Integration."""

import logging

import jubilant
import pytest
import requests

from tests.integration.helpers import fetch_container_json_logs, get_traces_patiently

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("flask_app", 8000),
        ("django_app", 8000),
        ("spring_boot_app", 8080),
        ("expressjs_app", 8080),
        ("fastapi_app", 8080),
        ("go_app", 8080),
    ],
)
def test_workload_tracing(
    juju: jubilant.Juju,
    app_fixture: str,
    port: int,
    request: pytest.FixtureRequest,
    session_with_retry: requests.Session,
):
    """
    arrange: Deploy Tempo cluster, app to test and postgres if required.
    act: Send 5 requests to the app.
    assert: Tempo should have tracing info about the app.
    """
    tempo_app = "tempo"
    if not juju.status().apps.get(tempo_app):
        request.getfixturevalue("tempo_app")

    app = request.getfixturevalue(app_fixture)

    juju.integrate(f"{app.name}:tracing", f"{tempo_app}:tracing")

    juju.wait(
        jubilant.all_active,
        timeout=10 * 60,
        delay=10,
    )
    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address
    tempo_host = status.apps[tempo_app].units[tempo_app + "/0"].address

    for _ in range(5):
        response = session_with_retry.get(f"http://{unit_ip}:{port}", timeout=5)
        assert response.status_code == 200

    # verify workload traces are ingested into Tempo
    assert get_traces_patiently(tempo_host, app.name)


def test_flask_access_logs_have_trace_correlation(
    juju: jubilant.Juju,
    flask_app,
    tempo_app,
    session_with_retry: requests.Session,
):
    """
    arrange: deploy Flask and Tempo, and relate tracing.
    act: send requests to Flask root endpoint.
    assert: gunicorn access logs include traceId and spanId.
    """
    try:
        juju.integrate(f"{flask_app.name}:tracing", f"{tempo_app.name}:tracing")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(
        lambda status: jubilant.all_active(status, flask_app.name, tempo_app.name),
        timeout=10 * 60,
        delay=10,
    )
    status = juju.status()
    unit_ip = status.apps[flask_app.name].units[f"{flask_app.name}/0"].address
    model_name = status.model.name
    pod_name = f"{flask_app.name}-0"

    for _ in range(5):
        response = session_with_retry.get(f"http://{unit_ip}:8000", timeout=5)
        assert response.status_code == 200

    all_logs = fetch_container_json_logs(pod_name, model_name, "flask-app")
    access_logs = [
        log
        for log in all_logs
        if log.get("attributes", {}).get("logger.name") == "gunicorn.access"
        and log.get("attributes", {}).get("url.path") == "/"
    ]
    assert access_logs, "No gunicorn.access log records for / found."
    assert any(
        "traceId" in log and "spanId" in log for log in access_logs[-20:]
    ), f"No trace correlation fields found in recent gunicorn.access logs: {access_logs[-5:]}"
