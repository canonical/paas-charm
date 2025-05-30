# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Global fixtures and utilities for integration and unit tests."""
import unittest

import pytest

from tests.unit.django.constants import DEFAULT_LAYER as DJANGO_DEFAULT_LAYER
from tests.unit.expressjs.constants import DEFAULT_LAYER as EXPRESSJS_DEFAULT_LAYER
from tests.unit.fastapi.constants import DEFAULT_LAYER as FASTAPI_DEFAULT_LAYER
from tests.unit.flask.constants import DEFAULT_LAYER as FLASK_DEFAULT_LAYER
from tests.unit.go.constants import DEFAULT_LAYER as GO_DEFAULT_LAYER


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
    parser.addoption("--expressjs-app-image", action="store")
    parser.addoption("--localstack-address", action="store")
    parser.addoption("--kube-config", action="store")


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


@pytest.fixture
def expressjs_container_mock():
    """Create a mock instance for the Container."""
    mock = unittest.mock.MagicMock()
    pull_result = unittest.mock.MagicMock()
    pull_result.read.return_value = str(EXPRESSJS_DEFAULT_LAYER["services"]).replace("'", '"')
    mock.pull.return_value = pull_result
    return mock
