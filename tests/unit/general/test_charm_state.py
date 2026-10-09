# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state unit tests."""

import pathlib
from unittest.mock import MagicMock

import pytest
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from paas_charm.charm_state import (
    CharmState,
    IntegrationRequirers,
    RelationDataError,
    framework_config_option_fields,
)
from paas_charm.flask.charm import FlaskConfig
from paas_charm.rabbitmq import InvalidRabbitMQRelationDataError
from paas_charm.s3 import InvalidS3RelationDataError
from paas_charm.saml import InvalidSAMLRelationDataError
from paas_charm.valkey import InvalidValkeyRelationDataError

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.mark.parametrize(
    "settings, names, expected",
    [
        pytest.param(
            {},
            {"public-option", "internal_name", "port"},
            {"public-option": "internal_name", "port": "port"},
            id="alias-only",
        ),
        pytest.param({}, {"internal_name", "port"}, {"port": "port"}, id="ignored-name"),
        pytest.param(
            {"populate_by_name": True},
            {"internal_name", "port"},
            {"internal_name": "internal_name", "port": "port"},
            id="name-enabled",
        ),
        pytest.param(
            {"populate_by_name": True},
            {"public-option", "internal_name", "port"},
            {"public-option": "internal_name", "port": "port"},
            id="alias-precedes-name",
        ),
        pytest.param(
            {"validate_by_alias": False, "validate_by_name": True},
            {"public-option", "internal_name", "port"},
            {"internal_name": "internal_name", "port": "port"},
            id="alias-disabled",
        ),
    ],
)
def test_framework_config_option_fields(settings, names, expected):
    """Assign ownership only to inputs accepted and selected by Pydantic."""

    class Config(BaseModel):
        model_config = ConfigDict(**settings)
        internal_name: str = Field(alias="public-option")
        port: int

    assert framework_config_option_fields(Config, names) == expected


@pytest.mark.parametrize(
    "names, expected", [({"first", "second"}, "first"), ({"second"}, "second")]
)
def test_framework_alias_choice_priority(names, expected):
    """Follow the same alias-choice priority as model validation."""

    class Config(BaseModel):
        value: int = Field(validation_alias=AliasChoices("first", "second"))

    assert framework_config_option_fields(Config, names) == {expected: "value"}


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


@pytest.mark.parametrize(
    "option, field", [("user-option", "user_option"), ("public_option", "public_option")]
)
def test_required_framework_alias_is_not_user_config(tmp_path, option, field):
    """Accept a required framework alias without mappings or duplicate app validation."""

    class ExtendedFlaskConfig(FlaskConfig):
        internal_name: str = Field(alias="public-option")

    (tmp_path / "config.yaml").write_text(
        "options:\n"
        "  public-option:\n"
        "    type: string\n"
        "    optional: false\n"
        f"  {option}:\n"
        "    type: string\n"
        "    optional: false\n"
    )
    state = CharmState.from_charm(
        charm_dir=tmp_path,
        config={"public-option": "configured", option: "ordinary"},
        framework="flask",
        framework_config=ExtendedFlaskConfig(**{"public-option": "configured"}),
        secret_key=MagicMock(is_ready=False),
        peers=MagicMock(is_related=False),
        integration_requirers=IntegrationRequirers(databases={}),
    )
    assert state.framework_config["internal_name"] == "configured"
    assert state.user_defined_config == {field: "ordinary"}
    assert state.config_options.options == {}
    assert state.framework_config_fields["public-option"] == "internal_name"
