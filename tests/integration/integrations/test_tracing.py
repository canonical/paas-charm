# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import logging

import jubilant
import pytest
import requests

from tests.integration.helpers import get_traces_patiently

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "tracing_app_fixture, port",
    [
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
        ("expressjs_app", 8080),
    ],
)
@pytest.mark.skip_juju_version("3.4")  # Tempo only supports Juju>=3.4
def test_workload_tracing(
    juju: jubilant.Juju,
    tracing_app_fixture: str,
    port: int,
    request: pytest.FixtureRequest,
):
    """
    arrange: Deploy Tempo cluster, app to test and postgres if required.
    act: Send 5 requests to the app.
    assert: Tempo should have tracing info about the app.
    """
    tempo_app = "tempo"
    if not juju.status().apps.get(tempo_app):
        request.getfixturevalue("tempo_app")
    tracing_app = request.getfixturevalue(tracing_app_fixture)

    juju.integrate(f"{tracing_app.name}:tracing", f"{tempo_app}:tracing")

    juju.wait(
        lambda status: jubilant.all_active(status, [tracing_app.name, tempo_app]), timeout=600
    )
    status = juju.status()
    unit_ip = status.apps[tracing_app.name].units[tracing_app.name + "/0"].address
    tempo_host = status.apps[tempo_app].units[tempo_app + "/0"].address

    for _ in range(5):
        requests.get(f"http://{unit_ip}:{port}")

    # verify workload traces are ingested into Tempo
    assert get_traces_patiently(tempo_host, tracing_app.name)

    juju.remove_relation(f"{tracing_app.name}:tracing", f"{tempo_app}:tracing", force=True)
    juju.remove_application(tracing_app.name, destroy_storage=True, force=True)