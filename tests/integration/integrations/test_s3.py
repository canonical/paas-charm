#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms S3 integration."""
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
def test_s3_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    port: int,
    juju: jubilant.Juju,
    s3_integrator_app: App,
    s3_credentials,
    s3_configuration,
):
    """
    arrange: after 12-Factor charm has been deployed.
    act: establish relations established with loki charm.
    assert: loki joins relation successfully, logs are being output to container and to files for
        loki to scrape.
    """
    app = request.getfixturevalue(app_fixture)
    juju.integrate(f"{app.name}:s3", f"{s3_integrator_app.name}:s3-credentials")

    juju.wait(
        lambda status: jubilant.all_active(status, app.name, s3_integrator_app.name),
        timeout=600,
        delay=3,
    )
    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address

    response = requests.get(f"http://{unit_ip}:{port}/env", timeout=5)
    assert response.status_code == 200
    env = response.json()

    assert env["S3_ACCESS_KEY"] == s3_credentials["access-key"]
    assert env["S3_SECRET_KEY"] == s3_credentials["secret-key"]
    assert env["S3_BUCKET"] == s3_configuration["bucket"]
    assert env["S3_ENDPOINT"] == s3_configuration["endpoint"]
    assert env["S3_PATH"] == s3_configuration["path"]
    assert env["S3_REGION"] == s3_configuration["region"]
    assert env["S3_URI_STYLE"] == s3_configuration["s3-uri-style"]

    # Check that it list_objects in the bucket. If the connection
    # is unsuccessful of the bucket does not exist, the code raises.
    response = requests.get(f"http://{unit_ip}:{port}/s3/status", timeout=5)
    assert response.status_code == 200
    assert "SUCCESS" == response.text
