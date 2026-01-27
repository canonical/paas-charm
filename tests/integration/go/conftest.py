# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for go charm integration tests."""

import os
import pathlib

import pytest


PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/go/charm")
