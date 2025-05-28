# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state unit tests."""

from unittest.mock import MagicMock

import pytest

from paas_charm.charm_state import (
    CharmConfigInvalidError,
    CharmState,
    IntegrationRequirers,
    InvalidSAMLRelationDataError,
)


@pytest.mark.parametrize(
    "error",
    [
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
