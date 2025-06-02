# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm integrations, like S3 and Saml."""
import logging
import urllib.parse

import ops
import pytest
import requests
from juju.application import Application
from juju.model import Model
from pytest_operator.plugin import OpsTest
from saml_test_helper import SamlK8sTestHelper

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("rabbitmq_server_integration")
async def test_rabbitmq_server_integration(
    flask_app: Application,
    get_unit_ips,
):
    """
    arrange: Flask and rabbitmq-server deployed
    act: Integrate flask with rabbitmq-server
    assert: Assert that RabbitMQ works correctly
    """
    await assert_rabbitmq_integration_correct(flask_app, get_unit_ips)


@pytest.mark.usefixtures("rabbitmq_k8s_integration")
async def test_rabbitmq_k8s_integration(
    flask_app: Application,
    get_unit_ips,
):
    """
    arrange: Flask and rabbitmq-k8s deployed
    act: Integrate flask with rabbitmq-k8s
    assert: Assert that RabbitMQ works correctly

    """
    await assert_rabbitmq_integration_correct(flask_app, get_unit_ips)


async def assert_rabbitmq_integration_correct(flask_app: Application, get_unit_ips):
    """Assert that rabbitmq works correctly sending and receiving a message."""
    for unit_ip in await get_unit_ips(flask_app.name):
        response = requests.get(f"http://{unit_ip}:8000/rabbitmq/send", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text

        response = requests.get(f"http://{unit_ip}:8000/rabbitmq/receive", timeout=5)
        assert response.status_code == 200
        assert "SUCCESS" == response.text


async def test_saml_integration(
    ops_test: OpsTest,
    flask_app: Application,
    model: Model,
    get_unit_ips,
    s3_configuration,
    s3_credentials,
    boto_s3_client,
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
    saml_helper = SamlK8sTestHelper.deploy_saml_idp(model.name)

    saml_integrator_app: Application = await model.deploy(
        "saml-integrator",
        channel="latest/edge",
        series="jammy",
        trust=True,
    )
    await model.wait_for_idle()
    saml_helper.prepare_pod(model.name, f"{saml_integrator_app.name}-0")
    saml_helper.prepare_pod(model.name, f"{flask_app.name}-0")
    await saml_integrator_app.set_config(
        {
            "entity_id": saml_helper.entity_id,
            "metadata_url": saml_helper.metadata_url,
        }
    )
    await model.wait_for_idle(idle_period=30)
    await model.add_relation(f"{saml_integrator_app.name}", f"{flask_app.name}")
    await model.wait_for_idle(
        idle_period=30,
        apps=[flask_app.name, saml_integrator_app.name],
        status="active",
    )
    for unit_ip in await get_unit_ips(flask_app.name):
        response = requests.get(f"http://{unit_ip}:8000/env", timeout=5)
        assert response.status_code == 200
        env = response.json()
        assert env["SAML_ENTITY_ID"] == saml_helper.entity_id
        assert env["SAML_METADATA_URL"] == saml_helper.metadata_url
        entity_id_url = urllib.parse.urlparse(saml_helper.entity_id)
        assert env["SAML_SINGLE_SIGN_ON_REDIRECT_URL"] == urllib.parse.urlunparse(
            entity_id_url._replace(path="sso")
        )
        assert env["SAML_SIGNING_CERTIFICATE"] in saml_helper.CERTIFICATE.replace("\n", "")
