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
                tls=False,
                tls_ca=None,
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
                "VALKEY_TLS": "false",
                "VALKEY_TLS_CA": "",
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
                tls=True,
                tls_ca="-----BEGIN CERTIFICATE-----\nMIIBxTC...",
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
                "VALKEY_TLS": "true",
                "VALKEY_TLS_CA": "-----BEGIN CERTIFICATE-----\nMIIBxTC...",
                "VALKEY_MODE": "",
                "VALKEY_VERSION": "8.0.0",
            },
            id="Valkey with TLS, no credentials",
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
