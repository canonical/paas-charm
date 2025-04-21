# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import logging

import jubilant
import pytest
import requests
from juju.application import Application

from tests.integration.helpers import get_mails_patiently

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "smtp_app_fixture, port",
    [
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
        ("expressjs_app", 8080),
    ],
)
@pytest.mark.skip_juju_version("3.4")
def test_smtp_integrations(
    juju: jubilant.Juju,
    smtp_app_fixture: Application,
    port,
    request: pytest.FixtureRequest,
    mailcatcher,
):
    """
    arrange: Build and deploy the charm. Integrate the charm with the smtp-integrator.
    act: Send an email from the charm.
    assert: The mailcatcher should have received the email.
    """
    smtp_config = {
        "auth_type": "none",
        "domain": "example.com",
        "host": mailcatcher.host,
        "port": mailcatcher.port,
    }
    smtp_integrator_app = "smtp-integrator"
    if not juju.status().apps.get(smtp_integrator_app):
        juju.deploy(smtp_integrator_app, channel="latest/edge", config=smtp_config)

    smtp_app = request.getfixturevalue(smtp_app_fixture)
    juju.wait(jubilant.all_active)

    juju.integrate(smtp_app.name, f"{smtp_integrator_app}:smtp")
    juju.wait(lambda status: jubilant.all_active(status, [smtp_app.name, smtp_integrator_app]))

    status = juju.status()
    unit_ip = status.apps[smtp_app.name].units[smtp_app.name + "/0"].address
    response = requests.get(f"http://{unit_ip}:{port}/send_mail", timeout=5)
    assert response.status_code == 200
    assert "Sent" in response.text

    mails = get_mails_patiently(mailcatcher.pod_ip)
    assert mails[0]
    assert "<tester@example.com>" in mails[0]["sender"]
    assert mails[0]["recipients"] == ["<test@example.com>"]
    assert mails[0]["subject"] == "hello"
    juju.remove_relation(smtp_app.name, f"{smtp_integrator_app}:smtp", force=True)
    juju.remove_application(smtp_app.name, destroy_storage=True, force=True)
