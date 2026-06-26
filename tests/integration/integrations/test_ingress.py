# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import jubilant
import pytest
import requests

from tests.integration.integrations.conftest import (
    HOSTNAME,
    gateway_lb_ip,
    ingress_relation,
    pin_dns,
)
from tests.integration.types import App


@pytest.mark.parametrize(
    "app_fixture, endpoint, expected_text",
    [
        ("django_app", "/len/users", None),
        ("expressjs_app", "/", None),
        ("fastapi_app", "/", None),
        ("flask_app", "/", None),
        ("go_app", "/", "Hello, World!! Path: /"),
        ("spring_boot_app", "/hello-world", None),
    ],
)
def test_ingress(
    juju: jubilant.Juju,
    app_fixture: App,
    endpoint: str,
    expected_text: str | None,
    request: pytest.FixtureRequest,
    ingress_provider: tuple[str, str],
    session_with_retry: requests.Session,
):
    app = request.getfixturevalue(app_fixture)
    # The shared session_with_retry fixture only mounts the retry adapter on
    # http://; reuse that same adapter for https:// without touching the fixture.
    session_with_retry.mount("https://", session_with_retry.get_adapter("http://"))
    with ingress_relation(juju, app, ingress_provider):
        lb_ip = gateway_lb_ip(juju, ingress_provider)
        with pin_dns(HOSTNAME, lb_ip):
            response = session_with_retry.get(
                f"https://{HOSTNAME}{endpoint}",
                verify=False,
                timeout=30,
            )
        assert response.status_code == 200
        if expected_text:
            assert response.text.strip() == expected_text
