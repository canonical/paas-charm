# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the ExpressJS unit test."""

import os
import pathlib
import typing

import pytest
from ops.testing import Harness

from examples.expressjs.charm.src.charm import ExpressJSCharm

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/expressjs/charm")


@pytest.fixture(name="harness")
def harness_fixture(container_name: str) -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(ExpressJSCharm)
    harness.set_leader()
    root = harness.get_filesystem_root(container_name)
    (root / "app").mkdir(parents=True)
    harness.set_can_connect(container_name, True)
    harness.add_relation(
        "postgresql",
        "postgresql-k8s",
        app_data={
            "database": "test-database",
            "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
            "password": "test-password",
            "username": "test-username",
        },
    )
    yield harness
    harness.cleanup()
