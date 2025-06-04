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
    "app_fixture, port",
    [
        ("expressjs_app", 8080),
        ("fastapi_app", 8080),
        ("go_app", 8080),
        ("flask_app", 8000),
        ("django_app", 8000),
    ],
)
def test_smtp_integrations(
    juju: jubilant.Juju,
    app_fixture: App,
    port,
    request: pytest.FixtureRequest,
    mailcatcher,
):
    """
    arrange: Build and deploy the charm. Integrate the charm with the smtp-integrator.
    act: Send an email from the charm.
    assert: The mailcatcher should have received the email.
    """
    app = request.getfixturevalue(app_fixture)
    smtp_config = {
        "auth_type": "none",
        "domain": "example.com",
        "host": mailcatcher.host,
        "port": mailcatcher.port,
    }
    smtp_integrator_app = "smtp-integrator"
    if not juju.status().apps.get(smtp_integrator_app):
        juju.deploy(smtp_integrator_app, channel="latest/edge", config=smtp_config)

    juju.wait(lambda status: jubilant.all_active(status, app.name, smtp_integrator_app))

    juju.integrate(app.name, f"{smtp_integrator_app}:smtp")
    juju.wait(lambda status: jubilant.all_active(status, app.name, smtp_integrator_app))

    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address
    response = requests.get(f"http://{unit_ip}:{port}/send_mail", timeout=5)
    assert response.status_code == 200
    assert "Sent" in response.text

    mails = get_mails_patiently(mailcatcher.pod_ip)
    assert mails[0]
    assert "<tester@example.com>" in mails[0]["sender"]
    assert mails[0]["recipients"] == ["<test@example.com>"]
    assert mails[0]["subject"] == "hello"
