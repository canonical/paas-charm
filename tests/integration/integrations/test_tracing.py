# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Tracing Integration."""
import logging
import time

import jubilant
import pytest
import requests

from tests.integration.helpers import get_traces_patiently

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "paas_app_fixture, port",
    [
        ("expressjs_app", 8080),
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
    ],
)
@pytest.mark.skip_juju_version("3.4")  # Tempo only supports Juju>=3.4
def test_workload_tracing(
    juju: jubilant.Juju,
    paas_app_fixture: str,
    port: int,
    request: pytest.FixtureRequest,
):
    """
    arrange: Deploy Tempo cluster, app to test and postgres if required.
    act: Send 5 requests to the app.
    assert: Tempo should have tracing info about the app.
    """
    paas_app = request.getfixturevalue(paas_app_fixture)
    tempo_app = "tempo"
    if not juju.status().apps.get(tempo_app):
        request.getfixturevalue("tempo_app")

    juju.integrate(f"{paas_app.name}:tracing", f"{tempo_app}:tracing")

    juju.wait(lambda status: jubilant.all_active(status, paas_app.name, tempo_app))
    juju.wait(lambda status: status.apps[paas_app.name].is_active, timeout=600)
    juju.wait(lambda status: status.apps[tempo_app].is_active)
    status = juju.status()
    unit_ip = status.apps[paas_app.name].units[paas_app.name + "/0"].address
    tempo_host = status.apps[tempo_app].units[tempo_app + "/0"].address

    for _ in range(5):
        requests.get(f"http://{unit_ip}:{port}")

    time.sleep(10)

    # verify workload traces are ingested into Tempo
    assert get_traces_patiently(tempo_host, paas_app.name)

    juju.remove_relation(f"{paas_app.name}:tracing", f"{tempo_app}:tracing", force=True)
    juju.remove_unit(paas_app.name, num_units=1, force=True)
    juju.remove_application(paas_app.name, destroy_storage=True, force=True)
