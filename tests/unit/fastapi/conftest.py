# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the fastapi unit test."""

import os
import pathlib
import sys
import typing

import pytest
from ops.testing import Harness

from examples.fastapi.charm.src.charm import FastAPICharm

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
_TEMPLATES_DIR = PROJECT_ROOT / "src" / "paas_charm" / "templates" / "fastapi"

if str(_TEMPLATES_DIR) not in sys.path:
    sys.path.insert(0, str(_TEMPLATES_DIR))


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/fastapi/charm")


@pytest.fixture(name="harness")
def harness_fixture(container_name: str) -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(FastAPICharm)
    harness.set_leader()
    root = harness.get_filesystem_root(container_name)
    (root / "app").mkdir(parents=True)
    harness.set_can_connect(container_name, True)
    harness.update_config({"non-optional-string": "non-optional-value"})

    yield harness
    harness.cleanup()
