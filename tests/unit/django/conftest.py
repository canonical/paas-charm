# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Django-local fixture names backed by shared parent fixtures."""

import pytest


@pytest.fixture(name="base_state")
def base_state_fixture(django_framework_state):
    """Expose the focused Django state under the framework-local name."""
    return django_framework_state


@pytest.fixture(name="base_state_no_database")
def base_state_no_database_fixture(django_framework_state_no_database):
    """Expose the no-database Django state under the framework-local name."""
    return django_framework_state_no_database
