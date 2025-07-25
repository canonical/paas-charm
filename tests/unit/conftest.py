# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Global fixtures and utilities for unit tests."""

import io
import json
from unittest.mock import MagicMock

import ops
import pytest

from paas_charm.database_migration import DatabaseMigrationStatus
from tests.unit.django.constants import DEFAULT_LAYER as DJANGO_DEFAULT_LAYER
from tests.unit.expressjs.constants import DEFAULT_LAYER as EXPRESSJS_DEFAULT_LAYER
from tests.unit.fastapi.constants import DEFAULT_LAYER as FASTAPI_DEFAULT_LAYER
from tests.unit.flask.constants import DEFAULT_LAYER as FLASK_DEFAULT_LAYER
from tests.unit.go.constants import DEFAULT_LAYER as GO_DEFAULT_LAYER

OAUTH_RELATION_DATA_EXAMPLE = {
    "authorization_endpoint": "https://traefik_ip/model_name-hydra/oauth2/auth",
    "introspection_endpoint": "http://hydra.model_name.svc.cluster.local:4445/admin/oauth2/introspect",
    "issuer_url": "https://traefik_ip/model_name-hydra",
    "jwks_endpoint": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
    "scope": "openid profile email",
    "token_endpoint": "https://traefik_ip/model_name-hydra/oauth2/token",
    "userinfo_endpoint": "https://traefik_ip/model_name-hydra/userinfo",
    "client_id": "test-client-id",
}


@pytest.fixture
def database_migration_mock():
    """Create a mock instance for the DatabaseMigration class."""
    mock = MagicMock()
    mock.status = DatabaseMigrationStatus.PENDING
    mock.script = None
    return mock


@pytest.fixture
def flask_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(FLASK_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def django_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(DJANGO_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def go_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(GO_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def fastapi_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(FASTAPI_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def expressjs_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(EXPRESSJS_DEFAULT_LAYER["services"]))
    return container
