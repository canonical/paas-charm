# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Oauth Integration."""

import json
import logging
import re

import jubilant
import pytest
import requests
from playwright.sync_api import expect, sync_playwright

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, endpoint",
    [
        ("go_app", "login/openid-connect"),
        ("fastapi_app", "login"),
        ("spring_boot_app", "oauth2/authorization/oidc"),
        ("flask_app", "login"),
        ("django_app", "auth_login"),
    ],
)
def test_oauth_integrations(
    juju: jubilant.Juju,
    app_fixture: App,
    endpoint,
    request: pytest.FixtureRequest,
    identity_bundle,
    browser_context_manager,
    http: requests.Session,
):
    """
    arrange: set up the test Juju model and deploy the workload charm.
    act: integrate with ingress and hydra.
    assert: the workload charm uses the Kratos charm as the idp.
    """
    test_email = "test@example.com"
    test_password = "Testing1"
    test_username = "admin"
    test_secret = "secret_password"

    app = request.getfixturevalue(app_fixture)
    status = juju.status()

    if not status.apps.get(app.name).relations.get("ingress"):
        juju.integrate(f"{app.name}", "traefik-public")

    juju.wait(
        jubilant.all_active,
        timeout=10 * 60,
        delay=5,
    )

    if not status.apps.get(app.name).relations.get("oidc"):
        juju.integrate(f"{app.name}", "hydra")

    juju.wait(
        jubilant.all_active,
        timeout=10 * 60,
        delay=5,
    )

    if not _admin_identity_exists(juju, test_email):
        juju.run(
            "kratos/0",
            "create-admin-account",
            {"email": test_email, "password": test_password, "username": test_username},
        )

    try:
        secret_id = juju.add_secret(test_secret, {"password": test_password})
    except jubilant.CLIError as e:
        if e.stderr != f'ERROR secret with name "{test_secret}" already exists\n':
            raise e
        secrets = json.loads(juju.cli("secrets", "--format", "json"))
        secret_id = [secret for secret in secrets if secrets[secret].get("name") == test_secret][0]

    juju.cli("grant-secret", secret_id, "kratos")
    result = juju.run(
        "kratos/0",
        "reset-password",
        {"email": test_email, "password-secret-id": secret_id.split(":")[-1]},
    )
    logger.info("results reset-password %s", result.results)

    res = json.loads(
        juju.run("traefik-public/0", "show-proxied-endpoints").results["proxied-endpoints"]
    )
    logger.info("result show-proxied %s", res)

    # make sure the app is alive
    response = http.get(res[app.name]["url"], timeout=5, verify=False)
    assert response.status_code == 200

    _assert_idp_login_success(res[app.name]["url"], endpoint, test_email, test_password)


def _admin_identity_exists(juju, test_email):
    try:
        res = juju.run("kratos/0", "get-identity", {"email": test_email})
        return res.status == "completed"
    except jubilant.TaskError as e:
        logger.info(f"Error checking admin identity: {e}")
        return False


def _assert_idp_login_success(app_url: str, endpoint: str, test_email: str, test_password: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto(f"{app_url}/{endpoint}")
        logger.info("Page content: %s", page.content())
        expect(page).not_to_have_title(re.compile("Sign in failed"))
        page.get_by_label("Email").fill(test_email)
        page.get_by_label("Password").fill(test_password)
        page.get_by_role("button", name="Sign in").click()
        expect(page).to_have_url(re.compile(f"^{app_url}/profile.*"))
        assert f"Welcome, {test_email}!" in page.content()
