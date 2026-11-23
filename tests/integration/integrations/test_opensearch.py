# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for the OpenSearch integration."""

import jubilant
import pytest
import requests

from tests.integration.helpers import relation_exists
from tests.integration.types import App

SPRING_BOOT_OPENSEARCH_PROPERTIES = {
    "opensearch.uris",
    "opensearch.username",
    "opensearch.password",
    "opensearch.restclient.ssl.bundle",
    "spring.ssl.bundle.pem.opensearch.truststore.certificate",
}


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("spring_boot_app", 8080),
    ],
)
def test_opensearch_integration(
    juju: jubilant.Juju,
    app_fixture: str,
    port: int,
    request: pytest.FixtureRequest,
    opensearch_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: deploy the 12-factor charm, and OpenSearch with TLS in a machine model.
    act: integrate the charm with OpenSearch.
    assert: the application gets the OpenSearch properties, and it can read the index that the
        charm requested over TLS.
    """
    app = request.getfixturevalue(app_fixture)

    try:
        juju.integrate(f"{app.name}:opensearch", opensearch_app.name)
        juju.wait(
            lambda status: relation_exists(status, app.name, "opensearch", opensearch_app.name)
            and jubilant.all_active(status, app.name),
            timeout=10 * 60,
            delay=10,
        )
        status = juju.status()
        unit_ip = status.apps[app.name].units[app.name + "/0"].address

        response = session_with_retry.get(f"http://{unit_ip}:{port}/opensearch/status", timeout=10)
        assert response.status_code == 200
        assert response.text == "SUCCESS"

        env = session_with_retry.get(f"http://{unit_ip}:{port}/env", timeout=5).json()
        assert {key for key in env if "opensearch" in key} == SPRING_BOOT_OPENSEARCH_PROPERTIES
        assert all(uri.startswith("https://") for uri in env["opensearch.uris"].split(","))
        assert env["opensearch.restclient.ssl.bundle"] == "opensearch"
    finally:
        juju.remove_relation(app.name, opensearch_app.name)
