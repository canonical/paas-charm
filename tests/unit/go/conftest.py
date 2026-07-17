# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the go unit test."""

import os
import pathlib
import typing

import pytest
from ops.testing import Harness

from examples.go.charm.src.charm import GoCharm

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/go/charm")


@pytest.fixture(name="harness")
def harness_fixture(container_name) -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(GoCharm)
    harness.set_leader()
    root = harness.get_filesystem_root(container_name)
    (root / "app").mkdir(parents=True)
    harness.set_can_connect(container_name, True)

    yield harness
    harness.cleanup()
