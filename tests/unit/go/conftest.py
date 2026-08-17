# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the go unit test."""

import os
import pathlib

import pytest
from ops import testing

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/go/charm")


@pytest.fixture(name="base_state")
def base_state_fixture():
    """State with the Go container and secret storage relation."""
    yield {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={"go_secret_key": "test"},
            )
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                _base_plan=DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
    }
