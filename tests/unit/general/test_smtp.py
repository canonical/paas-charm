# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""SMTP relation unit tests."""

from unittest.mock import MagicMock

import pytest

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
