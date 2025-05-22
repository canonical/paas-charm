# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Tracing Integration."""
import logging

import jubilant
import pytest
import requests

from tests.integration.helpers import get_traces_patiently

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("expressjs_app", 8080),
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
    ],
)
def test_workload_tracing(
    juju: jubilant.Juju,
    app_fixture: str,
    port: int,
    request: pytest.FixtureRequest,
):
    """
    arrange: Deploy Tempo cluster, app to test and postgres if required.
    act: Send 5 requests to the app.
    assert: Tempo should have tracing info about the app.
    """
    app = request.getfixturevalue(app_fixture)
    tempo_app = "tempo"
    if not juju.status().apps.get(tempo_app):
        request.getfixturevalue("tempo_app")

    juju.integrate(f"{app.name}:tracing", f"{tempo_app}:tracing")

    juju.wait(lambda status: jubilant.all_active(status, [app.name, tempo_app]), timeout=600)
    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address
    tempo_host = status.apps[tempo_app].units[tempo_app + "/0"].address

    for _ in range(5):
        requests.get(f"http://{unit_ip}:{port}")

    # verify workload traces are ingested into Tempo
    assert get_traces_patiently(tempo_host, app.name)

    juju.remove_application(app.name, destroy_storage=True, force=True)
