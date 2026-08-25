# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for application secret-key and peer coordination helpers."""

import unittest.mock

import pytest
from ops import testing

from paas_charm.charm import PaasCharm


def test_secret_key_created_on_leader_elected(flask_context, base_state):
    """
    arrange: A leader Flask charm without an application secret key.
    act: Emit the leader-elected event.
    assert: An application-owned secret key is created and readable.
    """
    state = testing.State(**{**base_state, "leader": True, "secrets": []})

    with flask_context(flask_context.on.leader_elected(), state) as manager:
        manager.run()

        assert manager.charm._secret_key.is_ready
        assert manager.charm._secret_key.get_secret_key()


def test_initial_leader_elected_does_not_reconcile(flask_context, base_state):
    """
    arrange: A leader Flask charm without an application secret key.
    act: Emit the leader-elected event.
    assert: The key is initialized without prematurely reconciling the workload.
    """
    state = testing.State(**{**base_state, "leader": True, "secrets": []})

    with (
        unittest.mock.patch.object(PaasCharm, "_reconcile") as reconcile,
        flask_context(flask_context.on.leader_elected(), state) as manager,
    ):
        manager.run()

        assert manager.charm._secret_key.is_ready

    reconcile.assert_not_called()


def test_established_leader_elected_reconciles(flask_context, base_state):
    """
    arrange: A leader Flask charm with an established application secret key.
    act: Emit the leader-elected event.
    assert: The workload is reconciled so it restarts under the new leader.
    """
    state = testing.State(**{**base_state, "leader": True})
    established_state = flask_context.run(flask_context.on.config_changed(), state)

    with (
        unittest.mock.patch.object(PaasCharm, "_reconcile") as reconcile,
        flask_context(flask_context.on.leader_elected(), established_state) as manager,
    ):
        existing_key = manager.charm._secret_key.get_secret_key()
        manager.run()

        assert manager.charm._secret_key.get_secret_key() == existing_key

    reconcile.assert_called_once_with()


def test_pre_start_leader_elected_does_not_reconcile(flask_context, base_state):
    """
    arrange: A leader Flask charm with a secret but a workload that has not started.
    act: Emit the leader-elected event.
    assert: Reconciliation waits for a later lifecycle event with complete relation data.
    """
    state = testing.State(**{**base_state, "leader": True})

    with (
        unittest.mock.patch.object(PaasCharm, "_reconcile") as reconcile,
        flask_context(flask_context.on.leader_elected(), state) as manager,
    ):
        manager.run()

    reconcile.assert_not_called()


def test_secret_key_not_created_by_non_leader(flask_context, base_state):
    """
    arrange: A non-leader Flask charm.
    act: Initialize application secret-key storage.
    assert: The application secret key remains unavailable.
    """
    state = testing.State(**{**base_state, "leader": False, "secrets": []})

    with flask_context(flask_context.on.update_status(), state) as manager:
        manager.charm._secret_key.initialize()

        assert not manager.charm._secret_key.is_ready

        manager.run()


def test_secret_key_initialization_is_idempotent(flask_context, base_state):
    """
    arrange: A leader Flask charm with an initialized application secret key.
    act: Initialize the storage again.
    assert: The existing secret value is retained.
    """
    state = testing.State(**{**base_state, "leader": True, "secrets": []})

    with flask_context(flask_context.on.update_status(), state) as manager:
        manager.charm._secret_key.initialize()
        initial_key = manager.charm._secret_key.get_secret_key()

        manager.charm._secret_key.initialize()

        assert manager.charm._secret_key.get_secret_key() == initial_key

        manager.run()


def test_secret_key_rotation_changes_value(flask_context, base_state):
    """
    arrange: A leader Flask charm with an initialized application secret key.
    act: Rotate the secret key.
    assert: Juju exposes a different current value.
    """
    state = testing.State(**{**base_state, "leader": True, "secrets": []})

    with flask_context(flask_context.on.update_status(), state) as manager:
        manager.charm._secret_key.initialize()
        initial_key = manager.charm._secret_key.get_secret_key()

        manager.charm._secret_key.rotate()

        assert manager.charm._secret_key.get_secret_key() != initial_key

        manager.run()


def test_missing_secret_key_raises(flask_context, base_state):
    """
    arrange: A Flask charm without an application secret key.
    act: Read and rotate the missing key.
    assert: Both operations report that initialization is incomplete.
    """
    state = testing.State(**{**base_state, "leader": False, "secrets": []})

    with flask_context(flask_context.on.update_status(), state) as manager:
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.charm._secret_key.get_secret_key()
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.charm._secret_key.rotate()

        manager.run()


def test_peers_not_related(flask_context, base_state):
    """
    arrange: A Flask charm without a peer relation.
    act: Inspect peer coordination state.
    assert: The peer relation is absent.
    """
    state = testing.State(**{**base_state, "relations": []})

    with flask_context(flask_context.on.update_status(), state) as manager:
        assert not manager.charm._peers.is_related
        assert manager.charm._peers.get_peer_unit_fqdns() is None

        manager.run()


def test_peer_unit_fqdns(flask_context, base_state):
    """
    arrange: A Flask charm with two peer units.
    act: Read peer unit FQDNs.
    assert: The peer FQDNs are returned in unit-name order.
    """
    state = testing.State(
        **{
            **base_state,
            "relations": [testing.PeerRelation("peers", peers_data={1: {}, 2: {}})],
        }
    )

    with flask_context(flask_context.on.update_status(), state) as manager:
        assert manager.charm._peers.get_peer_unit_fqdns() == [
            "flask-k8s-1.flask-k8s-endpoints.test-model.svc.cluster.local",
            "flask-k8s-2.flask-k8s-endpoints.test-model.svc.cluster.local",
        ]

        manager.run()
