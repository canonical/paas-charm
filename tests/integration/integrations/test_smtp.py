# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""

import logging

import pytest
import requests
from juju.application import Application
from juju.errors import JujuError
from juju.model import Model
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import get_mails_patiently

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "smtp_app_fixture, port",
    [
        ("flask_app", 8000),
        ("django_app", 8000),
        ("fastapi_app", 8080),
        ("go_app", 8080),
    ],
)
async def test_smtp_integrations(
    ops_test: OpsTest,
    smtp_app_fixture: Application,
    port,
    model: Model,
    get_unit_ips,
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
    try:
        smtp_integrator_app = await model.deploy(
            "smtp-integrator",
            channel="latest/edge",
            config=smtp_config,
        )
    except JujuError as e:
        if "application already exists" in str(e):
            logger.info(f"smtp-integrator is already deployed {e}")
            smtp_integrator_app = model.applications["smtp-integrator"]
        else:
            raise e

    smtp_app = request.getfixturevalue(smtp_app_fixture)
    await model.wait_for_idle()

    await model.add_relation(smtp_app.name, f"{smtp_integrator_app.name}:smtp")
    await model.wait_for_idle(
        idle_period=30,
        apps=[smtp_app.name, smtp_integrator_app.name],
        status="active",
    )

    unit_ip = (await get_unit_ips(smtp_app.name))[0]
    response = requests.get(f"http://{unit_ip}:{port}/send_mail", timeout=5)
    assert response.status_code == 200
    assert "Sent" in response.text

    mails = await get_mails_patiently(mailcatcher.pod_ip)
    assert mails[0]
    assert "<tester@example.com>" in mails[0]["sender"]
    assert mails[0]["recipients"] == ["<test@example.com>"]
    assert mails[0]["subject"] == "hello"
