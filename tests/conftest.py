# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Global fixtures and utilities for integration and unit tests."""
import unittest

import pytest

from paas_charm.database_migration import DatabaseMigrationStatus
from tests.unit.django.constants import DEFAULT_LAYER as DJANGO_DEFAULT_LAYER
from tests.unit.django.constants import DJANGO_CONTAINER_NAME
from tests.unit.fastapi.constants import DEFAULT_LAYER as FASTAPI_DEFAULT_LAYER
from tests.unit.fastapi.constants import FASTAPI_CONTAINER_NAME
from tests.unit.flask.constants import DEFAULT_LAYER as FLASK_DEFAULT_LAYER
from tests.unit.flask.constants import FLASK_CONTAINER_NAME
from tests.unit.go.constants import DEFAULT_LAYER as GO_DEFAULT_LAYER
from tests.unit.go.constants import GO_CONTAINER_NAME


def pytest_addoption(parser):
    """Define some command line options for integration and unit tests."""
    parser.addoption("--charm-file", action="extend", nargs="+", default=[])
    parser.addoption("--test-flask-image", action="store")
    parser.addoption("--test-async-flask-image", action="store")
    parser.addoption("--test-db-flask-image", action="store")
    parser.addoption("--django-app-image", action="store")
    parser.addoption("--django-async-app-image", action="store")
    parser.addoption("--fastapi-app-image", action="store")
    parser.addoption("--go-app-image", action="store")
    parser.addoption("--flask-minimal-app-image", action="store")
    parser.addoption("--localstack-address", action="store")
    parser.addoption("--kube-config", action="store")


@pytest.fixture
def database_migration_mock():
    """Create a mock instance for the DatabaseMigration class."""
    mock = unittest.mock.MagicMock()
    mock.status = DatabaseMigrationStatus.PENDING
    mock.script = None
    return mock


@pytest.fixture
def flask_container_mock():
    """Create a mock instance for the Container."""
    mock = unittest.mock.MagicMock()
    pull_result = unittest.mock.MagicMock()
    pull_result.read.return_value = str(FLASK_DEFAULT_LAYER["services"]).replace("'", '"')
    mock.pull.return_value = pull_result
    return mock


@pytest.fixture
def django_container_mock():
    """Create a mock instance for the Container."""
    mock = unittest.mock.MagicMock()
    pull_result = unittest.mock.MagicMock()
    pull_result.read.return_value = str(DJANGO_DEFAULT_LAYER["services"]).replace("'", '"')
    mock.pull.return_value = pull_result
    return mock


@pytest.fixture
def go_container_mock():
    """Create a mock instance for the Container."""
    mock = unittest.mock.MagicMock()
    pull_result = unittest.mock.MagicMock()
    pull_result.read.return_value = str(GO_DEFAULT_LAYER["services"]).replace("'", '"')
    mock.pull.return_value = pull_result
    return mock


@pytest.fixture
def fastapi_container_mock():
    """Create a mock instance for the Container."""
    mock = unittest.mock.MagicMock()
    pull_result = unittest.mock.MagicMock()
    pull_result.read.return_value = str(FASTAPI_DEFAULT_LAYER["services"]).replace("'", '"')
    mock.pull.return_value = pull_result
    return mock
