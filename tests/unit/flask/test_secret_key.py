# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for application secret-key and peer coordination helpers."""

import pytest

from .constants import DEFAULT_LAYER
from .constants import DEFAULT_LAYER


def test_secret_key_created_on_leader_elected(harness, container_name):
def test_secret_key_created_on_leader_elected(harness, container_name):
    """
    arrange: A leader Flask charm.
    act: Run the initial hooks.
    assert: An application-owned secret key is created and readable.
    """
    harness.set_leader(True)
    harness.model.unit.get_container(container_name).add_layer("a_layer", DEFAULT_LAYER)
    harness.model.unit.get_container(container_name).add_layer("a_layer", DEFAULT_LAYER)
    harness.begin_with_initial_hooks()

    assert harness.charm._secret_key.is_ready
    assert harness.charm._secret_key.get_secret_key()


def test_secret_key_not_created_by_non_leader(harness):
    """
    arrange: A non-leader Flask charm.
    act: Initialize application secret-key storage.
    assert: The application secret key remains unavailable.
    """
    harness.set_leader(False)
    harness.begin()

    harness.charm._secret_key.initialize()

    assert not harness.charm._secret_key.is_ready


def test_secret_key_initialization_is_idempotent(harness):
    """
    arrange: A leader Flask charm with an initialized application secret key.
    act: Initialize the storage again.
    assert: The existing secret value is retained.
    """
    harness.set_leader(True)
    harness.begin()
    harness.charm._secret_key.initialize()
    initial_key = harness.charm._secret_key.get_secret_key()

    harness.charm._secret_key.initialize()

    assert harness.charm._secret_key.get_secret_key() == initial_key


def test_secret_key_rotation_changes_value(harness):
    """
    arrange: A leader Flask charm with an initialized application secret key.
    act: Rotate the secret key.
    assert: Juju exposes a different current value.
    """
    harness.set_leader(True)
    harness.begin()
    harness.charm._secret_key.initialize()
    initial_key = harness.charm._secret_key.get_secret_key()

    harness.charm._secret_key.rotate()

    assert harness.charm._secret_key.get_secret_key() != initial_key


def test_missing_secret_key_raises(harness):
    """
    arrange: A Flask charm without an application secret key.
    act: Read and rotate the missing key.
    assert: Both operations report that initialization is incomplete.
    """
    harness.set_leader(False)
    harness.begin()

    with pytest.raises(RuntimeError, match="not initialized"):
        harness.charm._secret_key.get_secret_key()
    with pytest.raises(RuntimeError, match="not initialized"):
        harness.charm._secret_key.rotate()


def test_peers_not_related(harness):
    """
    arrange: A Flask charm without initial hooks.
    act: Inspect peer coordination state.
    assert: The peer relation is absent.
    """
    harness.begin()

    assert not harness.charm._peers.is_related
    assert harness.charm._peers.get_peer_unit_fqdns() is None


def test_peer_unit_fqdns(harness):
    """
    arrange: A Flask charm with two peer units.
    act: Read peer unit FQDNs.
    assert: The peer FQDNs are returned in unit-name order.
    """
    harness.set_model_name("test-model")
    harness.begin()
    relation_id = harness.add_relation("peers", harness.charm.app.name)
    harness.add_relation_unit(relation_id, f"{harness.charm.app.name}/2")
    harness.add_relation_unit(relation_id, f"{harness.charm.app.name}/1")

    assert harness.charm._peers.get_peer_unit_fqdns() == [
        "flask-k8s-1.flask-k8s-endpoints.test-model.svc.cluster.local",
        "flask-k8s-2.flask-k8s-endpoints.test-model.svc.cluster.local",
    ]
