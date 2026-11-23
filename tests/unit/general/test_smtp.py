# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""SMTP relation unit tests."""

from unittest.mock import MagicMock

import pytest
from charmlibs.interfaces.smtp import AuthType, SmtpRelationData, TransportSecurity

from paas_charm.exceptions import InvalidRelationInterfaceError
from paas_charm.smtp import SmtpRelation


def test_smtp_setup_invalid_relation_interface():
    """
    arrange: given a SMTP relation configured with an invalid interface.
    act: when the relation is set up.
    assert: InvalidRelationInterfaceError is raised.
    """
    mock_charm = MagicMock()
    mock_charm.framework.meta.requires["smtp"].interface_name = "invalid"
    relation = SmtpRelation.__new__(SmtpRelation)
    relation._charm = mock_charm

    with pytest.raises(
        InvalidRelationInterfaceError,
        match="Built-in SMTP relation interface is not 'smtp'",
    ):
        relation.setup(MagicMock())


def test_smtp_env_keeps_short_credentials():
    """
    arrange: given SMTP relation data whose user and password are substrings of "none".
    act: when the SMTP environment is generated.
    assert: the user and password are kept in the environment.
    """
    relation_data = SmtpRelationData(
        host="smtp.example.com",
        port=587,
        user="no",
        password="one",
        auth_type=AuthType.PLAIN,
        transport_security=TransportSecurity.STARTTLS,
        domain="example.com",
    )

    env = SmtpRelation._generate_smtp_env(relation_data)

    assert env["SMTP_USER"] == "no"
    assert env["SMTP_PASSWORD"] == "one"


def test_smtp_env_drops_none_values():
    """
    arrange: given SMTP relation data without credentials and with "none" auth and security.
    act: when the SMTP environment is generated.
    assert: the unset and "none" values are not in the environment.
    """
    relation_data = SmtpRelationData(
        host="smtp.example.com",
        port=25,
        auth_type=AuthType.NONE,
        transport_security=TransportSecurity.NONE,
        domain="example.com",
    )

    env = SmtpRelation._generate_smtp_env(relation_data)

    assert "SMTP_USER" not in env
    assert "SMTP_PASSWORD" not in env
    assert "SMTP_AUTH_TYPE" not in env
    assert "SMTP_TRANSPORT_SECURITY" not in env
