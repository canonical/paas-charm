# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the go unit test."""

import pathlib
import typing
from unittest import mock

import pytest
from ops import testing

from examples.go.charm.src.charm import GoCharm
from paas_charm.paas_config import read_paas_config

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
GO_CHARM_ROOT = PROJECT_ROOT / "examples/go/charm"


@pytest.fixture(name="go_context")
def go_context_fixture() -> typing.Generator[testing.Context[GoCharm], None, None]:
    """Context rooted at the Go example charm."""
    with (
        mock.patch(
            "paas_charm.charm.read_paas_config",
            return_value=read_paas_config(GO_CHARM_ROOT),
        ),
        testing.Context(GoCharm, charm_root=GO_CHARM_ROOT) as context,
    ):
        yield context


@pytest.fixture(name="base_state")
def base_state_fixture():
    """State with the Go container, application secret, and peer relation."""
    return {
        "leader": True,
        "secrets": [
            testing.Secret(
                tracked_content={"value": "test"},
                label="go-secret-key",
                owner="app",
            )
        ],
        "relations": [
            testing.PeerRelation("peers"),
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
