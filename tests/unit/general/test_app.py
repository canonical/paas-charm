# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""App unit tests."""
import pytest
from charms.saml_integrator.v0.saml import SamlEndpoint

from paas_charm.app import generate_saml_env
from paas_charm.saml import PaaSSAMLRelationData


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            PaaSSAMLRelationData.model_construct(
                entity_id="test-entity-id",
                metadata_url=None,
                certificates=("test-certificate-1",),
                endpoints=(
                    SamlEndpoint(
                        name="test-endpoint",
                        url="http://testing-endpoint.test",
                        binding="test-binding",
                        response_url="http://response-url.test",
                    ),
                ),
            ),
            {
                "SAML_ENTITY_ID": "test-entity-id",
                "SAML_SIGNING_CERTIFICATE": "test-certificate-1",
            },
            id="Minimum relation data",
        ),
        pytest.param(
            PaaSSAMLRelationData.model_construct(
                entity_id="https://login.staging.ubuntu.com",
                metadata_url="https://login.staging.ubuntu.com/saml/metadata",
                certificates=("https://login.staging.ubuntu.com/saml/", "test-certificate-2"),
                endpoints=(
                    SamlEndpoint(
                        name="single_sign_on_service_redirect_url",
                        url="http://testing-redirect-url.test",
                        binding="test-binding",
                        response_url="http://response-url.test",
                    ),
                    SamlEndpoint(
                        name="other_endpoint",
                        url="http://other-url.test",
                        binding="test-binding",
                        response_url="http://response-url.test",
                    ),
                ),
            ),
            {
                "SAML_ENTITY_ID": "https://login.staging.ubuntu.com",
                "SAML_METADATA_URL": "https://login.staging.ubuntu.com/saml/metadata",
                "SAML_SINGLE_SIGN_ON_REDIRECT_URL": "http://testing-redirect-url.test/",
                "SAML_SIGNING_CERTIFICATE": "https://login.staging.ubuntu.com/saml/,test-certificate-2",
            },
            id="All relation data",
        ),
    ],
)
def test_saml_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given SAML relation data.
    act: when generate_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_saml_env(relation_data) == expected_env
