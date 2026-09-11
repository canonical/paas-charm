# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the internal built-in relation classes."""

from unittest.mock import MagicMock

from paas_charm.valkey import (
    ValkeyRelation,
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


def test_valkey_relation_is_ready_with_data():
    """
    arrange: A ValkeyRelation containing valkey data.
    act: Call is_ready.
    assert: Returns True.
    """
    charm_mock = MagicMock()
    relation = _make_relation(charm_mock, ValkeyRelation, "valkey")
    relation._requirer = MagicMock()
    assert relation.is_ready() is True


def test_valkey_relation_not_ready_without_data():
    """
    arrange: A ValkeyRelation no valkey data, required.
    act: Call is_ready.
    assert: Returns False.
    """
    charm_mock = MagicMock()
    relation = _make_relation(charm_mock, ValkeyRelation, "valkey", optional=False)
    relation._requirer = MagicMock()
    relation._requirer.to_relation_data.return_value = None
    assert relation.is_ready() is False
