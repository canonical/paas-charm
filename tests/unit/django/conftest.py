# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pytest fixtures for the Django unit tests."""

# Framework Scenario fixtures intentionally share the same state structure.
# pylint: disable=R0801

import os
import pathlib

import pytest
from ops import pebble, testing

from tests.unit.conftest import postgresql_relation

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/django/charm")


def _base_state(*, with_database: bool) -> dict:
    """Build the common Scenario state for Django tests."""
    relations: list[testing.RelationBase] = [testing.PeerRelation("peers")]
    if with_database:
        relations.append(postgresql_relation("django-k8s"))
    container = testing.Container(
        name="app",
        can_connect=True,
        mounts={"config": testing.Mount(location="/django/gunicorn.conf.py", source="conf")},
        execs={
            testing.Exec(["/bin/python3"], return_code=0),
            testing.Exec(["python3", "-c", "import gevent"], return_code=0),
            testing.Exec(
                ["python3", "manage.py", "createsuperuser", "--noinput"],
                stdout="OK",
            ),
        },
        service_statuses={"django": pebble.ServiceStatus.INACTIVE},
        _base_plan=DEFAULT_LAYER,
    )
    return {
        "leader": True,
        "secrets": [
            testing.Secret(
                tracked_content={"value": "test"},
                label="app-secret-key",
                owner="app",
            ),
        ],
        "relations": relations,
        "containers": {container},
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture() -> dict:
    """Return a Django state with its required PostgreSQL integration."""
    return _base_state(with_database=True)


@pytest.fixture(scope="function", name="base_state_no_database")
def base_state_no_database_fixture() -> dict:
    """Return a Django state without a database integration."""
    return _base_state(with_database=False)
