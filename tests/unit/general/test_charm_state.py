# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state unit tests."""

import pathlib
from unittest.mock import MagicMock

import pytest

from paas_charm.charm_state import CharmConfigInvalidError, CharmState, IntegrationRequirers
from paas_charm.rabbitmq import InvalidRabbitMQRelationDataError
from paas_charm.redis import InvalidRedisRelationDataError
from paas_charm.s3 import InvalidS3RelationDataError
from paas_charm.saml import InvalidSAMLRelationDataError

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent.parent


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(
            InvalidRabbitMQRelationDataError("Invalid RabbitMQ relation data"),
            id="Invalid RabbitMQ relation data",
        ),
        pytest.param(
            InvalidRedisRelationDataError("Invalid Redis relation data"),
            id="Invalid Redis relation data",
        ),
        pytest.param(
            InvalidS3RelationDataError("Invalid S3 relation data"),
            id="Invalid S3 relation data",
        ),
        pytest.param(
            InvalidSAMLRelationDataError("Invalid SAML relation data"),
            id="Invalid SAML relation data",
        ),
    ],
)
def test_charm_state_integration_state_build_error(error):
    """Test invalid relation data errors."""
    saml_mock = MagicMock()
    saml_mock.to_relation_data.side_effect = error

    with pytest.raises(CharmConfigInvalidError):
        CharmState.from_charm(
            config=MagicMock(),
            framework="test",
            framework_config=MagicMock(),
            secret_storage=MagicMock(),
            integration_requirers=IntegrationRequirers(
                databases=MagicMock(),
                redis=MagicMock(),
                rabbitmq=MagicMock(),
                s3=MagicMock(),
                saml=saml_mock,
            ),
            base_url="http://test-base-url",
        )
