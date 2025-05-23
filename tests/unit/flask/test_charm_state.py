# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm state unit tests."""
import copy
import unittest.mock
from secrets import token_hex

import pytest

from paas_charm.charm_state import CharmState, IntegrationRequirers, S3RelationData
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.flask.charm import Charm

from .constants import SAML_APP_RELATION_DATA_EXAMPLE

# this is a unit test file
# pylint: disable=protected-access

DEFAULT_CHARM_CONFIG = {"flask-preferred-url-scheme": "HTTPS"}
SECRET_STORAGE_MOCK = unittest.mock.MagicMock(is_initialized=True)
SECRET_STORAGE_MOCK.get_secret_key.return_value = ""

CHARM_STATE_FLASK_CONFIG_TEST_PARAMS = [
    pytest.param(
        {"flask-env": "prod"}, {"env": "prod", "preferred_url_scheme": "HTTPS"}, id="env"
    ),
    pytest.param(
        {"flask-debug": True}, {"debug": True, "preferred_url_scheme": "HTTPS"}, id="debug"
    ),
    pytest.param(
        {"flask-secret-key": "1234"},
        {"secret_key": "1234", "preferred_url_scheme": "HTTPS"},
        id="secret-key",
    ),
    pytest.param(
        {"flask-preferred-url-scheme": "http"},
        {"preferred_url_scheme": "HTTP"},
        id="preferred-url-scheme",
    ),
]


@pytest.mark.parametrize("charm_config, flask_config", CHARM_STATE_FLASK_CONFIG_TEST_PARAMS)
def test_charm_state_flask_config(charm_config: dict, flask_config: dict) -> None:
    """
    arrange: none
    act: set flask_* charm configurations.
    assert: flask_config in the charm state should reflect changes in charm configurations.
    """
    config = copy.copy(DEFAULT_CHARM_CONFIG)
    config.update(charm_config)
    charm = unittest.mock.MagicMock(
        config=config, framework_config_class=Charm.framework_config_class
    )
    charm_state = CharmState.from_charm(
        framework="flask",
        framework_config=Charm.get_framework_config(charm),
        secret_storage=SECRET_STORAGE_MOCK,
        config=config,
        integration_requirers=IntegrationRequirers(databases={}),
    )
    assert charm_state.framework_config == flask_config


@pytest.mark.parametrize(
    "charm_config",
    [
        pytest.param({"flask-env": ""}, id="env"),
        pytest.param({"flask-secret-key": ""}, id="secret-key"),
        pytest.param(
            {"flask-preferred-url-scheme": "tls"},
            id="preferred-url-scheme",
        ),
    ],
)
def test_charm_state_invalid_flask_config(charm_config: dict) -> None:
    """
    arrange: none
    act: set flask_* charm configurations to be invalid values.
    assert: the CharmState should raise a CharmConfigInvalidError exception
    """
    config = copy.copy(DEFAULT_CHARM_CONFIG)
    config.update(charm_config)
    charm = unittest.mock.MagicMock(
        config=config, framework_config_class=Charm.framework_config_class
    )
    with pytest.raises(CharmConfigInvalidError) as exc:
        CharmState.from_charm(
            framework_config=Charm.get_framework_config(charm),
            secret_storage=SECRET_STORAGE_MOCK,
            config=config,
            integration_requirers=IntegrationRequirers(databases={}),
        )
    for config_key in charm_config:
        assert config_key in exc.value.msg


@pytest.mark.parametrize(
    "s3_connection_info, expected_s3_parameters",
    [
        pytest.param(None, None, id="empty"),
        pytest.param(
            (
                relation_data := {
                    "access-key": "access-key",
                    "secret-key": "secret-key",
                    "bucket": "bucket",
                }
            ),
            S3RelationData(**relation_data),
            id="with data",
        ),
    ],
)
def test_s3_integration(s3_connection_info, expected_s3_parameters):
    """
    arrange: Prepare charm and charm config.
    act: Create the CharmState with s3 information.
    assert: Check the S3Parameters generated are the expected ones.
    """
    config = copy.copy(DEFAULT_CHARM_CONFIG)
    config.update(config)
    charm = unittest.mock.MagicMock(config=config)
    charm_state = CharmState.from_charm(
        config=config,
        framework_config=Charm.get_framework_config(charm),
        framework="flask",
        secret_storage=SECRET_STORAGE_MOCK,
        integration_requirers=IntegrationRequirers(
            databases={}, s3=_s3_requirer_mock(s3_connection_info)
        ),
    )
    assert charm_state.integrations
    assert charm_state.integrations.s3 == expected_s3_parameters


@pytest.mark.parametrize(
    "s3_uri_style, addressing_style",
    [("host", "virtual"), ("path", "path"), (None, None)],
)
def test_s3_addressing_style(s3_uri_style, addressing_style) -> None:
    """
    arrange: Create s3 relation data with different s3_uri_styles.
    act: Create S3Parameters pydantic BaseModel from relation data.
    assert: Check that s3_uri_style is a valid addressing style.
    """
    s3_relation_data = {
        "access-key": token_hex(16),
        "secret-key": token_hex(16),
        "bucket": "backup-bucket",
        "region": "us-west-2",
        "s3-uri-style": s3_uri_style,
    }
    s3_parameters = S3RelationData(**s3_relation_data)
    assert s3_parameters.addressing_style == addressing_style


def test_saml_integration():
    """
    arrange: Prepare charm and charm config.
    act: Create the CharmState with saml information.
    assert: Check the SamlParameters generated are the expected ones.
    """
    saml_app_relation_data = dict(SAML_APP_RELATION_DATA_EXAMPLE)
    config = copy.copy(DEFAULT_CHARM_CONFIG)
    config.update(config)
    charm = unittest.mock.MagicMock(config=config)
    charm_state = CharmState.from_charm(
        config=config,
        framework_config=Charm.get_framework_config(charm),
        framework="flask",
        secret_storage=SECRET_STORAGE_MOCK,
        integration_requirers=IntegrationRequirers(
            databases={}, saml=_saml_requirer_mock(saml_app_relation_data)
        ),
    )
    assert charm_state.integrations
    assert charm_state.integrations.saml_parameters
    saml_parameters = charm_state.integrations.saml_parameters
    assert saml_parameters.entity_id == saml_app_relation_data["entity_id"]
    assert saml_parameters.metadata_url == saml_app_relation_data["metadata_url"]
    assert (
        saml_parameters.single_sign_on_redirect_url
        == saml_app_relation_data["single_sign_on_service_redirect_url"]
    )
    assert saml_parameters.signing_certificate == saml_app_relation_data["x509certs"].split(",")[0]


def _test_saml_integration_invalid_parameters():
    params = []
    params.append(
        pytest.param(
            {},
            ["Invalid Saml"],
            id="Empty relation data",
        )
    )
    saml_app_relation_data = dict(SAML_APP_RELATION_DATA_EXAMPLE)
    del saml_app_relation_data["single_sign_on_service_redirect_url"]
    params.append(
        pytest.param(
            saml_app_relation_data,
            ["Invalid Saml", "single_sign_on_service_redirect_url"],
            id="Missing single_sign_on_service_redirect_url",
        )
    )
    saml_app_relation_data = dict(SAML_APP_RELATION_DATA_EXAMPLE)
    del saml_app_relation_data["x509certs"]
    params.append(
        pytest.param(
            saml_app_relation_data,
            ["Invalid Saml", "x509certs"],
            id="Missing x509certs",
        )
    )
    saml_app_relation_data = dict(SAML_APP_RELATION_DATA_EXAMPLE)
    saml_app_relation_data["x509certs"] = ""
    params.append(
        pytest.param(
            saml_app_relation_data,
            ["Invalid Saml", "x509certs"],
            id="Empty x509certs",
        )
    )
    return params


@pytest.mark.parametrize(
    "saml_app_relation_data, error_messages", _test_saml_integration_invalid_parameters()
)
def test_saml_integration_invalid(saml_app_relation_data, error_messages):
    """
    arrange: Prepare a saml relation data that is invalid.
    act: Try to build CharmState.
    assert: It should raise CharmConfigInvalidError with a specific error message.
    """
    config = copy.copy(DEFAULT_CHARM_CONFIG)
    config.update(config)
    charm = unittest.mock.MagicMock(config=config)
    with pytest.raises(CharmConfigInvalidError) as exc:
        charm_state = CharmState.from_charm(
            config=config,
            framework_config=Charm.get_framework_config(charm),
            framework="flask",
            secret_storage=SECRET_STORAGE_MOCK,
            integration_requirers=IntegrationRequirers(
                databases={}, saml=_saml_requirer_mock(saml_app_relation_data)
            ),
        )
    for message in error_messages:
        assert message in str(exc)


def test_secret_configuration():
    """
    arrange: prepare a juju secret configuration.
    act: set secret-test charm configurations.
    assert: user_defined_config in the charm state should contain the value of the secret configuration.
    """
    config = copy.copy(DEFAULT_CHARM_CONFIG)
    config["secret-test"] = {"foo": "foo", "bar": "bar", "foo-bar": "foobar"}
    charm = unittest.mock.MagicMock(
        config=config,
        framework_config_class=Charm.framework_config_class,
    )
    charm_state = CharmState.from_charm(
        framework="flask",
        framework_config=Charm.get_framework_config(charm),
        secret_storage=SECRET_STORAGE_MOCK,
        config=config,
        integration_requirers=IntegrationRequirers(databases={}),
    )
    assert "secret_test" in charm_state.user_defined_config
    assert charm_state.user_defined_config["secret_test"] == {
        "bar": "bar",
        "foo": "foo",
        "foo-bar": "foobar",
    }


def test_flask_secret_key_id_no_value():
    """
    arrange: Prepare an invalid flask-secret-key-id secret.
    act: Try to build CharmState.
    assert: It should raise CharmConfigInvalidError.
    """
    config = copy.copy(DEFAULT_CHARM_CONFIG)
    config["flask-secret-key-id"] = {"value": "foobar"}
    charm = unittest.mock.MagicMock(
        config=config,
        framework_config_class=Charm.framework_config_class,
    )
    with pytest.raises(CharmConfigInvalidError) as exc:
        CharmState.from_charm(
            framework="flask",
            framework_config=Charm.get_framework_config(charm),
            secret_storage=SECRET_STORAGE_MOCK,
            config=config,
            database_requirers={},
        )


def test_flask_secret_key_id_duplication():
    """
    arrange: Provide both the flask-secret-key-id and flask-secret-key configuration.
    act: Try to build CharmState.
    assert: It should raise CharmConfigInvalidError.
    """
    config = copy.copy(DEFAULT_CHARM_CONFIG)
    config["flask-secret-key"] = "test"
    config["flask-secret-key-id"] = {"value": "foobar"}
    charm = unittest.mock.MagicMock(
        config=config,
        framework_config_class=Charm.framework_config_class,
    )
    with pytest.raises(CharmConfigInvalidError) as exc:
        CharmState.from_charm(
            framework="flask",
            framework_config=Charm.get_framework_config(charm),
            secret_storage=SECRET_STORAGE_MOCK,
            config=config,
            database_requirers={},
        )


def _s3_requirer_mock(relation_data: dict[str:str] | None) -> unittest.mock.MagicMock | None:
    """S3 requirer mock."""
    if not relation_data:
        return None
    s3 = unittest.mock.MagicMock()
    s3.to_relation_data.return_value = S3RelationData(**relation_data)
    return s3


def _saml_requirer_mock(relation_data: dict[str:str]) -> unittest.mock.MagicMock:
    """Saml requirer mock."""
    saml = unittest.mock.MagicMock()
    saml.get_relation_data.return_value.to_relation_data.return_value = relation_data
    return saml
