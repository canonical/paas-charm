# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the expressjs unit test."""
import os
import pathlib
import typing

import pytest
from ops.testing import Harness

from examples.expressjs.charm.src.charm import ExpressJSCharm

from .constants import EXPRESSJS_CONTAINER_NAME

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/expressjs/charm")


@pytest.fixture(name="harness")
def harness_fixture() -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(ExpressJSCharm)
    harness.set_leader()
    root = harness.get_filesystem_root(EXPRESSJS_CONTAINER_NAME)
    (root / "app").mkdir(parents=True)
    harness.set_can_connect(EXPRESSJS_CONTAINER_NAME, True)

    yield harness
    harness.cleanup()
