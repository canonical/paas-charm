# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Oauth Integration."""

import json
import logging
import re
from uuid import uuid4

import pytest
from playwright.sync_api import expect, sync_playwright

logger = logging.getLogger(__name__)

import logging

import jubilant
import pytest

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, endpoint",
    [
        # ("spring_boot_app", "login"),
        # ("expressjs_app", "login"),
        # ("fastapi_app", "login"),
        # ("go_app", "login"),
        ("flask_app", "login"),
        ("django_app", "auth_login"),
    ],
)
def test_outh_integrations(
    juju: jubilant.Juju,
    app_fixture: App,
    endpoint,
    request: pytest.FixtureRequest,
    identity_bundle,
):
    """
    arrange: set up the test Juju model.
    act: build and deploy the workload charm with required services.
    assert: the workload charm uses the Kratos charm as the idp.
    """
    app = request.getfixturevalue(app_fixture)
    status = juju.status()

    if not status.apps.get(app.name).relations.get("oidc"):
        juju.integrate(f"{app.name}", "hydra")

    if not status.apps.get(app.name).relations.get("ingress"):
        juju.integrate(f"{app.name}", "traefik-public")
    juju.wait(
        jubilant.all_active,
        timeout=30 * 60,
    )

    def admin_identity_exists():
        """Check if the admin identity exists in Kratos."""
        try:
            res = juju.run("kratos/0", "get-identity", {"email": "test@example.com"})
            return res.status == "completed"
        except jubilant.TaskError as e:
            logger.info(f"Error checking admin identity: {e}")
            return False

    if not admin_identity_exists():
        juju.run(
            "kratos/0",
            "create-admin-account",
            {"email": "test@example.com", "password": "Testing1", "username": "admin"},
        )
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

    res = json.loads(
        juju.run("traefik-public/0", "show-proxied-endpoints").results["proxied-endpoints"]
    )
    login_to_idp(res[app.name]["url"], endpoint)

    # Cleanup
    juju.run("kratos/0", "delete-identity", {"email": "test@example.com"})


def login_to_idp(app_url: str, endpoint: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(f"{app_url}/{endpoint}")
        expect(page).not_to_have_title(re.compile("Sign in failed"))
        page.get_by_label("Email").fill("test@example.com")
        page.get_by_label("Password").fill("Testing1")
        page.get_by_role("button", name="Sign in").click()
        expect(page).to_have_url(re.compile(f"^{app_url}/profile.*"))
        expect(page.get_by_role("heading", name="Welcome, test@example.com!")).to_be_visible()
