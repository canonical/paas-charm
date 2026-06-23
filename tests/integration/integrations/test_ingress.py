# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

import jubilant
import pytest
import requests

from tests.integration.integrations.conftest import HOSTNAME, gateway_lb_ip
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
):
    app = request.getfixturevalue(app_fixture)
    gateway_app, configurator_app = ingress_provider
    try:
        juju.integrate(app.name, configurator_app)
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err
    juju.wait(
        lambda status: jubilant.all_active(status, app.name, gateway_app, configurator_app),
        timeout=10 * 60,
        delay=5,
    )
    lb_ip = gateway_lb_ip(juju, ingress_provider)
    response = requests.get(
        f"https://{lb_ip}{endpoint}",
        headers={"Host": HOSTNAME},
        verify=False,
        timeout=30,
    )
    assert response.status_code == 200
    if expected_text:
        assert response.text.strip() == expected_text
