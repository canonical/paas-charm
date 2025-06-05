# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the Springboot unit test."""
import os
import pathlib
import typing

import pytest
from ops.testing import Harness

from examples.springboot.charm.src.charm import SpringBootCharm

from .constants import SPRINGBOOT_CONTAINER_NAME

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/springboot/charm")


@pytest.fixture(name="harness")
def harness_fixture() -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = Harness(SpringBootCharm)
    harness.set_leader()
    root = harness.get_filesystem_root(SPRINGBOOT_CONTAINER_NAME)
    (root / "app").mkdir(parents=True)
    harness.set_can_connect(SPRINGBOOT_CONTAINER_NAME, True)
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
