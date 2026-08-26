# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""ExpressJS-local fixture names backed by shared parent fixtures."""

import pytest


@pytest.fixture(name="base_state")
def base_state_fixture(expressjs_framework_state):
    """Expose the focused ExpressJS state under the framework-local name."""
    return expressjs_framework_state
