# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""SAML charm integration unit tests."""
from unittest.mock import MagicMock

import pytest
from charms.saml_integrator.v0.saml import SamlEndpoint, SamlRelationData
from pydantic import ValidationError

from paas_charm.saml import InvalidSAMLRelationDataError, PaaSSAMLRelationData, PaaSSAMLRequirer


@pytest.mark.parametrize(
    "relation_data, expected_relation_data",
    [
        pytest.param(
            None,
            None,
            id="none relation data",
        ),
        pytest.param(
            SamlRelationData(
                entity_id="test-entity-id",
                metadata_url=None,
                certificates=["cert1"],
                endpoints=[
                    SamlEndpoint(
                        name="test-endpoint", url=None, binding="test-binding", response_url=None
                    )
                ],
            ),
            PaaSSAMLRelationData(
                entity_id="test-entity-id",
                metadata_url=None,
                certificates=["cert1"],
                endpoints=[
                    SamlEndpoint(
                        name="test-endpoint", url=None, binding="test-binding", response_url=None
                    )
                ],
            ),
            id="minimum relation data",
        ),
        pytest.param(
            SamlRelationData(
                entity_id="test-entity-id",
                metadata_url="http://metadata-url.test",
                certificates=["cert1", "cert2"],
                endpoints=[
                    SamlEndpoint(
                        name="test-endpoint",
                        url="http://test-url.test",
                        binding="test-binding",
                        response_url="http://test-response-url.test",
                    ),
                    SamlEndpoint(
                        name="test-endpoint-2",
                        url="http://test-url.test",
                        binding="test-binding-2",
                        response_url="http://test-response-url.test",
                    ),
                ],
            ),
            PaaSSAMLRelationData(
                entity_id="test-entity-id",
                metadata_url="http://metadata-url.test",
                certificates=["cert1", "cert2"],
                endpoints=[
                    SamlEndpoint(
                        name="test-endpoint",
                        url="http://test-url.test",
                        binding="test-binding",
                        response_url="http://test-response-url.test",
                    ),
                    SamlEndpoint(
                        name="test-endpoint-2",
                        url="http://test-url.test",
                        binding="test-binding-2",
                        response_url="http://test-response-url.test",
                    ),
                ],
            ),
            id="maximum relation data",
        ),
    ],
)
def test_paas_saml_requirer_to_relation_data(relation_data, expected_relation_data):
    """
    arrange: given test relation data.
    act: when to_relation_data is called on PaaSSAMLRequirer.
    assert: expected relation data is returned.
    """
    saml_requirer = PaaSSAMLRequirer(charm=MagicMock())
    saml_requirer.get_relation_data = MagicMock(return_value=relation_data)

    relation_data = saml_requirer.to_relation_data()
    assert relation_data == expected_relation_data


def test_paas_saml_relation_data_properties():
    """Test PaaSSAMLRelationData properties."""
    relation_data = PaaSSAMLRelationData(
        entity_id="test-entity-id",
        metadata_url="http://metadata-url.test",
        certificates=["cert1", "cert2"],
        endpoints=[
            SamlEndpoint(
                name="test-endpoint",
                url="http://test-url.test",
                binding="test-binding",
                response_url="http://test-response-url.test",
            ),
            SamlEndpoint(
                name="SingleSignOnService",
                url="http://test-single-signon-url.test",
                binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                response_url="http://test-response-url.test",
            ),
        ],
    )

    assert relation_data.signing_certificate == "cert1"
    assert relation_data.single_sign_on_redirect_url == "http://test-single-signon-url.test/"


def test_paas_saml_relation_data_invalid():
    """
    arrange: given mocked get_relation_data function that raises ValidationError.
    act: when to_relation_data is called.
    assert: InvalidSAMLRelationDataError is raised.
    """
    saml_requirer = PaaSSAMLRequirer(charm=MagicMock())
    saml_requirer.get_relation_data = MagicMock(
        side_effect=ValidationError(MagicMock(), MagicMock())
    )

    with pytest.raises(InvalidSAMLRelationDataError) as exc:
        saml_requirer.to_relation_data()

    assert "Invalid PaaSSAMLRelationData" in str(exc.value)
