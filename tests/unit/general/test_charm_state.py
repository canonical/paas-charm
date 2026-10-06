# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state unit tests."""

import pathlib
from unittest.mock import MagicMock

import pytest
from pydantic import Field

from paas_charm.charm_state import CharmState, IntegrationRequirers, RelationDataError
from paas_charm.flask.charm import FlaskConfig
from paas_charm.rabbitmq import InvalidRabbitMQRelationDataError
from paas_charm.s3 import InvalidS3RelationDataError
from paas_charm.saml import InvalidSAMLRelationDataError
from paas_charm.valkey import InvalidValkeyRelationDataError

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(
            InvalidRabbitMQRelationDataError("Invalid RabbitMQ relation data"),
            id="Invalid RabbitMQ relation data",
        ),
        pytest.param(
            InvalidValkeyRelationDataError("Invalid Valkey relation data"),
            id="Invalid Valkey relation data",
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
    with pytest.raises(RelationDataError):
        CharmState.from_charm(
            charm_dir=f"{PROJECT_ROOT}/examples/flask/charm",
            config=MagicMock(),
            framework="test",
            framework_config=FlaskConfig(),
            secret_key=MagicMock(),
            peers=MagicMock(),
            integration_requirers=IntegrationRequirers(
                databases=MagicMock(),
                valkey=MagicMock(),
                rabbitmq=MagicMock(),
                s3=MagicMock(),
                saml=saml_mock,
            ),
            base_url="http://test-base-url",
        )


def test_required_framework_alias_is_not_user_config(tmp_path):
    """Accept a required framework alias without mappings or duplicate app validation."""

    class ExtendedFlaskConfig(FlaskConfig):
        internal_name: str = Field(alias="public-option")

    (tmp_path / "config.yaml").write_text(
        "options:\n"
        "  public-option:\n"
        "    type: string\n"
        "    optional: false\n"
        "  user-option:\n"
        "    type: string\n"
        "    optional: false\n"
    )
    state = CharmState.from_charm(
        charm_dir=tmp_path,
        config={"public-option": "configured", "user-option": "ordinary"},
        framework="flask",
        framework_config=ExtendedFlaskConfig(**{"public-option": "configured"}),
        secret_key=MagicMock(is_ready=False),
        peers=MagicMock(is_related=False),
        integration_requirers=IntegrationRequirers(databases={}),
    )
    assert state.framework_config["internal_name"] == "configured"
    assert state.user_defined_config == {"user_option": "ordinary"}
    assert state.config_options.options == {}
