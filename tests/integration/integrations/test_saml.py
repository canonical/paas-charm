#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for 12Factor charms SAML integration."""
import logging
import urllib.parse

import jubilant
import pytest
import requests
from saml_test_helper import SamlK8sTestHelper

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "app_fixture, port",
    [
        ("flask_app", 8000),
    ],
)
def test_saml_integration(
    request: pytest.FixtureRequest,
    app_fixture: str,
    port: int,
    juju: jubilant.Juju,
    s3_configuration,
    s3_credentials,
):
    """
    arrange: Integrate the Charm with saml-integrator, with a real SP.
    act: Call the endpoint to get env variables.
    assert: Valid Saml env variables should be in the workload.
    """
    # The goal of this test is not to test Saml in a real application, as it is not really
    # necessary, but that the integration with the saml-integrator is correct and the Saml
    # variables get injected into the workload.
    # However, for saml-integrator to get the metadata, we need a real SP, so SamlK8sTestHelper is
    # used to not have a dependency to an external SP.
    app = request.getfixturevalue(app_fixture)

    model_name = juju.status().model.name
    saml_helper = SamlK8sTestHelper.deploy_saml_idp(model_name)

    saml_integrator_app_name = "saml-integrator"
    juju.deploy(
        saml_integrator_app_name,
        channel="latest/edge",
        base="ubuntu@22.04",
        trust=True,
    )

    juju.wait(lambda status: jubilant.all_blocked(status, saml_integrator_app_name), timeout=600)

    saml_helper.prepare_pod(model_name, f"{saml_integrator_app_name}-0")
    saml_helper.prepare_pod(model_name, f"{app.name}-0")

    juju.config(
        saml_integrator_app_name,
        {
            "entity_id": saml_helper.entity_id,
            "metadata_url": saml_helper.metadata_url,
        },
    )

    juju.integrate(saml_integrator_app_name, app.name)

    juju.wait(
        lambda status: jubilant.all_active(status, saml_integrator_app_name, app.name),
        timeout=600,
    )

    status = juju.status()
    unit_ip = status.apps[app.name].units[app.name + "/0"].address
    response = requests.get(f"http://{unit_ip}:{port}/env", timeout=5)
    assert response.status_code == 200
    env = response.json()
    assert env["SAML_ENTITY_ID"] == saml_helper.entity_id
    assert env["SAML_METADATA_URL"] == saml_helper.metadata_url
    entity_id_url = urllib.parse.urlparse(saml_helper.entity_id)
    assert env["SAML_SINGLE_SIGN_ON_REDIRECT_URL"] == urllib.parse.urlunparse(
        entity_id_url._replace(path="sso")
    )
    assert env["SAML_SIGNING_CERTIFICATE"] in saml_helper.CERTIFICATE.replace("\n", "")
