# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm state unit tests."""
import copy
import unittest.mock
from secrets import token_hex

import pytest

import paas_charm
from paas_charm.charm_state import (
    CharmState,
    IntegrationRequirers,
    S3Parameters,
    SamlParameters,
    _create_configuration_attribute,
    generate_relation_parameters,
)
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.flask.charm import Charm

from .constants import INTEGRATIONS_RELATION_DATA, SAML_APP_RELATION_DATA_EXAMPLE

# this is a unit test file
# pylint: disable=protected-access

DEFAULT_CHARM_CONFIG = {"flask-preferred-url-scheme": "HTTPS", "non-optional-test": "something"}
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
            S3Parameters(**relation_data),
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
    assert charm_state.integrations.s3_parameters == expected_s3_parameters


def test_s3_integration_raises():
    """
    arrange: Prepare charm and charm config.
    act: Create the CharmState with s3 information that is invalid.
    assert: Check that CharmConfigInvalidError is raised.
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
                databases={}, s3=_s3_requirer_mock({"bucket": "bucket"})
            ),
        )
    assert "S3" in str(exc)


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
    s3_parameters = S3Parameters(**s3_relation_data)
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
    assert: app_config in the charm state should contain the value of the secret configuration.
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
    assert "secret_test" in charm_state.app_config
    assert charm_state.app_config["secret_test"] == {
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
    s3.get_s3_connection_info.return_value = relation_data
    return s3


def _saml_requirer_mock(relation_data: dict[str:str]) -> unittest.mock.MagicMock:
    """Saml requirer mock."""
    saml = unittest.mock.MagicMock()
    saml.get_relation_data.return_value.to_relation_data.return_value = relation_data
    return saml


def _test_app_config_parameters():
    non_optional_options = [
        {
            "name": (config_name_1 := "non_optional_bool"),
            "type_dict": {"type": "boolean", "optional": False},
            "type_result": (config_name_1, (bool, ...)),
        },
        {
            "name": (config_name_2 := "non_optional_int"),
            "type_dict": {"type": "int", "optional": False},
            "type_result": (config_name_2, (int, ...)),
        },
        {
            "name": (config_name_3 := "non_optional_float"),
            "type_dict": {"type": "float", "optional": False},
            "type_result": (config_name_3, (float, ...)),
        },
        {
            "name": (config_name_4 := "non_optional_str"),
            "type_dict": {"type": "string", "optional": False},
            "type_result": (config_name_4, (str, ...)),
        },
        {
            "name": (config_name_5 := "non_optional_secret"),
            "type_dict": {"type": "secret", "optional": False},
            "type_result": (config_name_5, (dict, ...)),
        },
    ]
    explicit_optional_options = [
        {
            "name": (config_name := f"explicit{option['name'][3:]}"),
            "type_dict": {"type": option["type_dict"]["type"], "optional": True},
            "type_result": (config_name, (option["type_result"][1][0] | None, None)),
        }
        for option in non_optional_options
    ]
    implicit_optional_options = [
        {
            "name": (config_name := f"implicit{option['name'][3:]}"),
            "type_dict": {"type": option["type_dict"]["type"]},
            "type_result": (config_name, (option["type_result"][1][0] | None, None)),
        }
        for option in non_optional_options
    ]

    all_options = implicit_optional_options + explicit_optional_options + non_optional_options
    return [
        pytest.param(option["name"], option["type_dict"], option["type_result"], id=option["name"])
        for option in all_options
    ]


@pytest.mark.parametrize(
    "option_name, option_dict, expected_output", _test_app_config_parameters()
)
def test_app_config(option_name, option_dict, expected_output):
    """
    arrange: Provide dictionaries for optional and non optional config options.
    act: Create an attribute.
    assert: The resultant attribute should have the correct type.
    """
    assert _create_configuration_attribute(option_name, option_dict) == expected_output


def _test_app_config_factory_parameters():
    mock_yaml = {
        "options": {
            (config_name_1 := "bool"): {"type": "boolean", "optional": False},
            (config_name_2 := "optional-bool"): {"type": "boolean", "optional": True},
            (config_name_3 := "int"): {"type": "int", "optional": False},
            (config_name_4 := "optional-int"): {"type": "int", "optional": True},
            (config_name_5 := "float"): {"type": "float", "optional": False},
            (config_name_6 := "optional-float"): {"type": "float", "optional": True},
            (config_name_7 := "str"): {"type": "string", "optional": False},
            (config_name_8 := "optional-str"): {"type": "string", "optional": True},
            (config_name_9 := "secret"): {"type": "secret", "optional": False},
            (config_name_10 := "optional-secret"): {"type": "secret", "optional": True},
            (config_name_11 := "flask-option"): {"type": "string"},
            (config_name_12 := "webserver-option"): {"type": "string"},
            (config_name_13 := "app-option"): {"type": "string"},
        }
    }
    expected_output = {
        config_name_1: bool,
        config_name_2.replace("-", "_"): bool | None,
        config_name_3: int,
        config_name_4.replace("-", "_"): int | None,
        config_name_5: float,
        config_name_6.replace("-", "_"): float | None,
        config_name_7: str,
        config_name_8.replace("-", "_"): str | None,
        config_name_9: dict,
        config_name_10.replace("-", "_"): dict | None,
    }
    return [
        pytest.param(mock_yaml, expected_output),
    ]


@pytest.mark.parametrize("mock_yaml, expected_output", _test_app_config_factory_parameters())
def test_app_config_factory(mock_yaml: dict, expected_output: dict, monkeypatch):
    """
    arrange: Provide mock config yaml with optional and non optional config options.
    act: Create an AppConfig object.
    assert: The resultant AppConfig object should have the required parameters set correctly.
        The AppConfig object should not have attributes for framework settings.
    """
    monkeypatch.setattr(
        "paas_charm.charm_state._config_metadata",
        unittest.mock.MagicMock(return_value=mock_yaml),
    )

    assert paas_charm.charm_state.app_config_factory("flask").__annotations__ == expected_output


def test_generate_relation_parameters_saml():
    """
    arrange: None
    act: Generate SamlParameters object.
    assert: The resultant object should be type of SamlParameters.
    """
    saml_parameters = generate_relation_parameters(
        SAML_APP_RELATION_DATA_EXAMPLE, SamlParameters, True
    )
    assert isinstance(saml_parameters, SamlParameters)


def test_generate_relation_parameters_saml_empty():
    """
    arrange: None
    act: Generate an empty SamlParameters object.
    assert: The resultant object should be type of None.
    """
    saml_parameters = generate_relation_parameters({}, SamlParameters)
    assert saml_parameters is None


def test_generate_relation_parameters_saml_fail():
    """
    arrange: None
    act: Generate an SamlParameters object with wrong integration data.
    assert: It should raise CharmConfigInvalidError.
    """
    with pytest.raises(paas_charm.exceptions.CharmConfigInvalidError):
        generate_relation_parameters({"wrong_key": "wrong_value"}, SamlParameters)


def test_generate_relation_parameters_s3():
    """
    arrange: None
    act: Generate S3Parameters object.
    assert: The resultant object should be type of S3Parameters.
    """
    s3_parameters = generate_relation_parameters(
        INTEGRATIONS_RELATION_DATA["s3"]["app_data"], S3Parameters
    )

    assert isinstance(s3_parameters, S3Parameters)


def test_generate_relation_parameters_s3_fail():
    """
    arrange: None
    act: Generate an S3Parameters object with empty integration data.
    assert: It should raise S3Parameters.
    """
    with pytest.raises(paas_charm.exceptions.CharmConfigInvalidError):
        generate_relation_parameters({}, S3Parameters, True)
