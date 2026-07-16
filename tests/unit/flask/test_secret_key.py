# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the SecretKeyStorage and Peers helpers."""

from .constants import DEFAULT_LAYER, FLASK_CONTAINER_NAME


def test_secret_key_created_on_leader_elected(harness):
    """
    arrange: a leader flask charm.
    act: run the initial hooks (fires leader-elected).
    assert: the application secret key secret exists and is readable.
    """
    harness.set_leader(True)
    harness.model.unit.get_container(FLASK_CONTAINER_NAME).add_layer("a_layer", DEFAULT_LAYER)
    harness.begin_with_initial_hooks()

    assert harness.charm._secret_key.is_ready
    key = harness.charm._secret_key.get_secret_key()
    assert isinstance(key, str)
    assert len(key) > 0


def test_secret_key_not_ready_before_creation(harness):
    """
    arrange: a flask charm that has not created its secret key yet.
    act: begin without initial hooks (no leader-elected).
    assert: the secret key is not ready.
    """
    harness.begin()

    assert not harness.charm._secret_key.is_ready


def test_secret_key_rotate_changes_value(harness):
    """
    arrange: a leader flask charm with an initialized secret key.
    act: rotate the secret key.
    assert: the secret key value changes.
    """
    harness.set_leader(True)
    harness.model.unit.get_container(FLASK_CONTAINER_NAME).add_layer("a_layer", DEFAULT_LAYER)
    harness.begin_with_initial_hooks()
    before = harness.charm._secret_key.get_secret_key()

    harness.charm._secret_key.rotate()

    after = harness.charm._secret_key.get_secret_key()
    assert before != after
