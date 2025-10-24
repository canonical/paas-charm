# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for http-proxy integration."""

import logging

import jubilant
import pytest
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("flask_app", 8000),
    ],
)
def test_proxy_integration(
    juju: jubilant.Juju,
    app_fixture: str,
    http_proxy_app: App,
    port,
    request: pytest.FixtureRequest,
    http: requests.Session,
):
    """
    arrange: Deploy 12-factor app and http proxy configurator correctly configured.
    act: Relate the http proxy configurator with the 12-factor app.
    assert: The correct proxy env vars from the relation are set in the 12-factor app.
    """
    app = request.getfixturevalue(app_fixture)
    try:
        juju.integrate(app.name, http_proxy_app.name)
        juju.wait(
            lambda status: status.apps[app.name].is_active,
            timeout=5 * 30,
            delay=10,
        )

        status = juju.status()
        unit_ip = status.apps[app.name].units[app.name + "/0"].address

        json_response = http.get(f"http://{unit_ip}:{port}/env", timeout=10).json()
        assert json_response["HTTPS_PROXY"] == "http://proxy.example.com:3128/"
        assert json_response["HTTP_PROXY"] == "http://proxy.example.com:3128/"
    finally:
        juju.remove_relation(app.name, http_proxy_app.name)
