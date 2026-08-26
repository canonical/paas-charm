# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go-local fixture names backed by shared parent fixtures."""

import pytest


@pytest.fixture(name="base_state")
def base_state_fixture(go_framework_state):
    """Expose the focused Go state under the framework-local name."""
    return go_framework_state
