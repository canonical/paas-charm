# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the internal built-in relation classes."""

from unittest.mock import MagicMock

import pytest

from paas_charm.exceptions import RelationDataError
from paas_charm.valkey import (
    InvalidValkeyRelationDataError,
    ValkeyMultipleRelationsNotSupportedError,
    ValkeyRelation,
    ValkeyTLSNotSupportedError,
)


def _make_relation(charm_mock, relation_class, relation_name, optional=True):
    """Build a builtin relation instance with minimal mocking.

    Args:
        charm_mock: A mock charm to parent the relation.
        relation_class: The builtin relation class to instantiate.
        relation_name: The endpoint name.
        optional: Whether the endpoint is optional in metadata.

    Returns:
        An instantiated relation with _required and _context set.
    """
    relation = relation_class.__new__(relation_class)
    relation.relation_name = relation_name
    relation._charm = charm_mock
    relation._context = MagicMock()
    relation._required = not optional
    relation._requirer = None
    return relation


@pytest.mark.parametrize("optional", [True, False])
def test_valkey_relation_ensure_ready_with_data(optional):
    """
    arrange: A ValkeyRelation containing valkey data.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    charm_mock = MagicMock()
    relation = _make_relation(charm_mock, ValkeyRelation, "valkey", optional=optional)
    relation._requirer = MagicMock()
    assert relation.ensure_ready() is None
    relation._requirer.to_relation_data.assert_called_once_with()


@pytest.mark.parametrize("optional", [True, False])
def test_valkey_relation_not_ready_without_data(optional):
    """
    arrange: A configured ValkeyRelation with no Valkey data.
    act: Call ensure_ready.
    assert: Raises RelationDataError identifying the Valkey endpoint.
    """
    charm_mock = MagicMock()
    relation = _make_relation(charm_mock, ValkeyRelation, "valkey", optional=optional)
    relation._requirer = MagicMock()
    relation._requirer.to_relation_data.return_value = None
    with pytest.raises(RelationDataError, match="Valkey relation data is not ready") as exc:
        relation.ensure_ready()
    assert exc.value.relation == "valkey"


def test_valkey_relation_ensure_ready_when_not_configured():
    """
    arrange: A ValkeyRelation without a configured requirer.
    act: Call ensure_ready.
    assert: Returns None without raising an exception.
    """
    relation = _make_relation(MagicMock(), ValkeyRelation, "valkey")
    assert relation.ensure_ready() is None


@pytest.mark.parametrize(
    "error_type",
    [
        InvalidValkeyRelationDataError,
        ValkeyMultipleRelationsNotSupportedError,
        ValkeyTLSNotSupportedError,
    ],
)
def test_valkey_relation_ensure_ready_wraps_invalid_data(error_type):
    """
    arrange: A ValkeyRelation whose requirer rejects invalid or unsupported data.
    act: Call ensure_ready.
    assert: RelationDataError preserves the original message, endpoint, and cause.
    """
    relation = _make_relation(MagicMock(), ValkeyRelation, "valkey")
    relation._requirer = MagicMock()
    error = error_type("Invalid Valkey data")
    relation._requirer.to_relation_data.side_effect = error
    with pytest.raises(RelationDataError, match="Invalid Valkey data") as exc:
        relation.ensure_ready()
    assert type(exc.value) is RelationDataError
    assert str(exc.value) == str(error)
    assert exc.value.relation == "valkey"
    assert exc.value.__cause__ is error
