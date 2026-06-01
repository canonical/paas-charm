# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Valkey unit tests."""

from unittest.mock import MagicMock, patch

import pytest

from paas_charm.app import generate_valkey_env
from paas_charm.valkey import ValkeyClientRequirer


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            MagicMock(
                endpoints="valkey-primary:6379",
                username="relation-1-abc123",
                password="supersecretpass",
                mode="sentinel",
                version="9.0.1",
            ),
            {
                "VALKEY_DB_CONNECT_STRING": "valkey://valkey-primary:6379",
                "VALKEY_DB_FRAGMENT": "",
                "VALKEY_DB_HOSTNAME": "valkey-primary",
                "VALKEY_DB_NETLOC": "valkey-primary:6379",
                "VALKEY_DB_PARAMS": "",
                "VALKEY_DB_PATH": "",
                "VALKEY_DB_PORT": "6379",
                "VALKEY_DB_QUERY": "",
                "VALKEY_DB_SCHEME": "valkey",
                "VALKEY_USERNAME": "relation-1-abc123",
                "VALKEY_PASSWORD": "supersecretpass",
                "VALKEY_MODE": "sentinel",
                "VALKEY_VERSION": "9.0.1",
            },
            id="Full valkey relation data",
        ),
        pytest.param(
            MagicMock(
                endpoints="valkey-host:6380",
                username=None,
                password=None,
                mode=None,
                version="8.0.0",
            ),
            {
                "VALKEY_DB_CONNECT_STRING": "valkey://valkey-host:6380",
                "VALKEY_DB_FRAGMENT": "",
                "VALKEY_DB_HOSTNAME": "valkey-host",
                "VALKEY_DB_NETLOC": "valkey-host:6380",
                "VALKEY_DB_PARAMS": "",
                "VALKEY_DB_PATH": "",
                "VALKEY_DB_PORT": "6380",
                "VALKEY_DB_QUERY": "",
                "VALKEY_DB_SCHEME": "valkey",
                "VALKEY_USERNAME": "",
                "VALKEY_PASSWORD": "",
                "VALKEY_MODE": "",
                "VALKEY_VERSION": "8.0.0",
            },
            id="Valkey without credentials",
        ),
    ],
)
def test_valkey_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given Valkey relation data (ValkeyResponseModel).
    act: when generate_valkey_env is called.
    assert: expected environment variables are generated.
    """
    assert generate_valkey_env(relation_data) == expected_env


@patch("paas_charm.valkey.ResourceRequirerEventHandler")
def test_valkey_to_relation_data_no_relations(mock_handler_cls):
    """
    arrange: given ValkeyClientRequirer with no relations.
    act: when to_relation_data is called.
    assert: None is returned.
    """
    mock_handler = MagicMock()
    mock_handler.relations = []
    mock_handler_cls.return_value = mock_handler

    mock_charm = MagicMock()
    requirer = ValkeyClientRequirer(charm=mock_charm, relation_name="valkey")

    assert requirer.to_relation_data() is None


@patch("paas_charm.valkey.ResourceRequirerEventHandler")
def test_valkey_to_relation_data_with_response(mock_handler_cls):
    """
    arrange: given ValkeyClientRequirer with one relation and a valid model.
    act: when to_relation_data is called.
    assert: ValkeyResponseModel is returned directly.
    """
    mock_relation = MagicMock()
    mock_relation.id = 1
    mock_relation.app = "valkey"

    mock_response = MagicMock()
    mock_response.endpoints = "valkey-primary:6379"
    mock_response.username = "testuser"
    mock_response.password = "testpass"
    mock_response.tls = False

    mock_model = MagicMock()
    mock_model.requests = [mock_response]

    mock_handler = MagicMock()
    mock_handler.relations = [mock_relation]
    mock_handler.interface.build_model.return_value = mock_model
    mock_handler_cls.return_value = mock_handler

    mock_charm = MagicMock()
    requirer = ValkeyClientRequirer(charm=mock_charm, relation_name="valkey")

    result = requirer.to_relation_data()
    assert result == mock_response
    mock_handler.interface.build_model.assert_called_once_with(1, component="valkey")


@patch("paas_charm.valkey.ResourceRequirerEventHandler")
def test_valkey_to_relation_data_empty_requests(mock_handler_cls):
    """
    arrange: given ValkeyClientRequirer with one relation but empty requests.
    act: when to_relation_data is called.
    assert: None is returned.
    """
    mock_relation = MagicMock()
    mock_relation.id = 1
    mock_relation.app = "valkey"

    mock_model = MagicMock()
    mock_model.requests = []

    mock_handler = MagicMock()
    mock_handler.relations = [mock_relation]
    mock_handler.interface.build_model.return_value = mock_model
    mock_handler_cls.return_value = mock_handler

    mock_charm = MagicMock()
    requirer = ValkeyClientRequirer(charm=mock_charm, relation_name="valkey")

    assert requirer.to_relation_data() is None


@patch("paas_charm.valkey.ResourceRequirerEventHandler")
def test_valkey_to_relation_data_tls_not_supported(mock_handler_cls):
    """
    arrange: given ValkeyClientRequirer with TLS enabled in relation data.
    act: when to_relation_data is called.
    assert: ValkeyTLSNotSupportedError is raised.
    """
    from paas_charm.valkey import ValkeyTLSNotSupportedError

    mock_relation = MagicMock()
    mock_relation.id = 1
    mock_relation.app = "valkey"

    mock_response = MagicMock()
    mock_response.endpoints = "valkey-primary:6379"
    mock_response.username = "testuser"
    mock_response.password = "testpass"
    mock_response.tls = True

    mock_model = MagicMock()
    mock_model.requests = [mock_response]

    mock_handler = MagicMock()
    mock_handler.relations = [mock_relation]
    mock_handler.interface.build_model.return_value = mock_model
    mock_handler_cls.return_value = mock_handler

    mock_charm = MagicMock()
    requirer = ValkeyClientRequirer(charm=mock_charm, relation_name="valkey")

    with pytest.raises(ValkeyTLSNotSupportedError):
        requirer.to_relation_data()


@patch("paas_charm.valkey.ResourceRequirerEventHandler")
def test_valkey_to_relation_data_multiple_relations_not_supported(mock_handler_cls):
    """
    arrange: given ValkeyClientRequirer with more than one relation.
    act: when to_relation_data is called.
    assert: ValkeyMultipleRelationsNotSupportedError is raised.
    """
    from paas_charm.valkey import ValkeyMultipleRelationsNotSupportedError

    mock_relation_1 = MagicMock()
    mock_relation_1.id = 1
    mock_relation_1.app = "valkey-1"

    mock_relation_2 = MagicMock()
    mock_relation_2.id = 2
    mock_relation_2.app = "valkey-2"

    mock_handler = MagicMock()
    mock_handler.relations = [mock_relation_1, mock_relation_2]
    mock_handler_cls.return_value = mock_handler

    mock_charm = MagicMock()
    requirer = ValkeyClientRequirer(charm=mock_charm, relation_name="valkey")

    with pytest.raises(ValkeyMultipleRelationsNotSupportedError):
        requirer.to_relation_data()