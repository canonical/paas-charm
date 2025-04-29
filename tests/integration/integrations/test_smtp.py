# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for SMTP Integration."""

import logging

import jubilant
import pytest
import requests

from tests.integration.helpers import get_mails_patiently
from tests.integration.types import App

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
@pytest.mark.skip_juju_version("3.4")
def test_smtp_integrations(
    juju: jubilant.Juju,
    paas_app_fixture: App,
    port,
    request: pytest.FixtureRequest,
    mailcatcher,
):
    """
    arrange: Build and deploy the charm. Integrate the charm with the smtp-integrator.
    act: Send an email from the charm.
    assert: The mailcatcher should have received the email.
    """
    paas_app = request.getfixturevalue(paas_app_fixture)
    smtp_config = {
        "auth_type": "none",
        "domain": "example.com",
        "host": mailcatcher.host,
        "port": mailcatcher.port,
    }
    smtp_integrator_app = "smtp-integrator"
    if not juju.status().apps.get(smtp_integrator_app):
        juju.deploy(smtp_integrator_app, channel="latest/edge", config=smtp_config)

    juju.wait(lambda status: status.apps[paas_app.name].is_active)
    juju.wait(lambda status: status.apps[smtp_integrator_app].is_active)

    juju.integrate(paas_app.name, f"{smtp_integrator_app}:smtp")
    juju.wait(lambda status: status.apps[paas_app.name].is_active)
    juju.wait(lambda status: status.apps[smtp_integrator_app].is_active)

    status = juju.status()
    unit_ip = status.apps[paas_app.name].units[paas_app.name + "/0"].address
    response = requests.get(f"http://{unit_ip}:{port}/send_mail", timeout=5)
    assert response.status_code == 200
    assert "Sent" in response.text

    mails = get_mails_patiently(mailcatcher.pod_ip)
    assert mails[0]
    assert "<tester@example.com>" in mails[0]["sender"]
    assert mails[0]["recipients"] == ["<test@example.com>"]
    assert mails[0]["subject"] == "hello"

    juju.remove_relation(paas_app.name, f"{smtp_integrator_app}:smtp", force=True)
    juju.remove_unit(paas_app.name, num_units=1, force=True)
    juju.remove_application(paas_app.name, destroy_storage=True, force=True)
