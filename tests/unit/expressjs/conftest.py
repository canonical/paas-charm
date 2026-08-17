# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the ExpressJS unit test."""

import os
import pathlib

import pytest
from ops import testing

from tests.unit.conftest import postgresql_relation

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/expressjs/charm")


@pytest.fixture(name="base_state")
def base_state_fixture():
    """State with the ExpressJS container and required relations."""
    yield {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"expressjs_secret_key": "test"}
            ),
            postgresql_relation("test-database"),
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
