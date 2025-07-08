# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for SMTP Integration."""

import json
import logging
import re
from uuid import uuid4

import pytest
import requests
from playwright.sync_api import expect, sync_playwright

logger = logging.getLogger(__name__)

pytest_plugins = ["oauth_tools.fixtures"]
import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port, endpoint",
    [
        # ("spring_boot_app", 8080),
        # ("expressjs_app", 8080),
        ("fastapi_app", 8080, "login"),
        # ("go_app", 8080),
        ("flask_app", 8000, "login"),
        ("django_app", 8000, "auth_login"),
    ],
)
def test_oidc_integrations(
    juju: jubilant.Juju,
    app_fixture: App,
    port,
    endpoint,
    request: pytest.FixtureRequest,
    http: requests.Session,
    identity_bundle,
    pytestconfig: pytest.Config,
):
    """
    arrange: set up the test Juju model.
    act: build and deploy the Penpot charm with required services.
    assert: the Penpot charm becomes active.
    """
    app = request.getfixturevalue(app_fixture)
    juju.integrate(f"{app.name}", "traefik-public")
    juju.integrate(f"{app.name}:receive-ca-cert", "self-signed-certificates:send-ca-cert")
    juju.wait(
        jubilant.all_active,
        timeout=30 * 60,
    )
    juju.integrate(f"{app.name}:oauth", "hydra")
    juju.wait(
        jubilant.all_active,
        timeout=30 * 60,
    )
    juju.run(
        "kratos/0",
        "create-admin-account",
        {"email": "test@example.com", "password": "Testing1", "username": "admin"},
    ).results
    # add secret password
    password_name = str(uuid4())
    secret_id = juju.add_secret(password_name, {"password": "Testing1"})
    # grant secret to kratos
    juju.cli("grant-secret", secret_id, "kratos")
    # run kratos action to reset password
    juju.run(
        "kratos/0",
        "reset-password",
        {"email": "test@example.com", "password-secret-id": secret_id.split(":")[-1]},
    )
    # juju run kratos/0 reset-password email=test3@example.com password-secret-id=d1ifqhnmp25c77uf5gug

    res = json.loads(
        juju.run("traefik-public/0", "show-proxied-endpoints").results["proxied-endpoints"]
    )
    app_url = res[app.name]["url"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(f"{app_url}/{endpoint}")
        # Fill an input.
        expect(page).not_to_have_title(re.compile("Sign in failed"))
        page.locator("#\\:r1\\:").fill("test@example.com")
        page.locator("#\\:r4\\:").fill("Testing1")
        page.get_by_role("button", name="Sign in").click()
        expect(page).to_have_url(re.compile(f"^{app_url}/profile.*"))

    # Cleanup
    juju.run("kratos/0", "delete-identity", {"email": "test@example.com"})
