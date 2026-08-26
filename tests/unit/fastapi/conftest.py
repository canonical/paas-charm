# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""FastAPI-local fixture names backed by shared parent fixtures."""

import pytest


@pytest.fixture(name="base_state")
def base_state_fixture(fastapi_framework_state):
    """Expose the focused FastAPI state under the framework-local name."""
    return fastapi_framework_state
