# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Global fixtures and utilities for unit tests."""
import unittest

import pytest

from paas_charm.database_migration import DatabaseMigrationStatus


@pytest.fixture
def database_migration_mock():
    """Create a mock instance for the DatabaseMigration class."""
    mock = unittest.mock.MagicMock()
    mock.status = DatabaseMigrationStatus.PENDING
    mock.script = None
    return mock
