# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the integration test."""
import os
import pathlib
import textwrap
import typing
import unittest.mock

import ops
import pytest
from ops.testing import Harness

from examples.django.charm.src.charm import DjangoCharm
from paas_charm.database_migration import DatabaseMigrationStatus

from .constants import DEFAULT_LAYER, DJANGO_CONTAINER_NAME

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/django/charm")


@pytest.fixture(name="harness")
def harness_fixture() -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture."""
    harness = _build_harness()
    yield harness
    harness.cleanup()


@pytest.fixture(name="harness_no_integrations")
def harness_no_integrations_fixture() -> typing.Generator[Harness, None, None]:
    """Ops testing framework harness fixture without a database."""
    meta = textwrap.dedent(
        """
    name: django-k8s

    bases:
      - build-on:
          - name: ubuntu
            channel: "22.04"
        run-on:
          - name: ubuntu
            channel: "22.04"

    summary: An example Django application.

    description: An example Django application.

    containers:
      django-app:
        resource: django-app-image

    peers:
      secret-storage:
        interface: secret-storage
    provides:
      grafana-dashboard:
        interface: grafana_dashboard
      metrics-endpoint:
        interface: prometheus_scrape
    requires:
      ingress:
        interface: ingress
        limit: 1
      logging:
        interface: loki_push_api
    """
    )
    harness = _build_harness(meta)
    yield harness
    harness.cleanup()


@pytest.fixture
def database_migration_mock():
    """Create a mock instance for the DatabaseMigration class."""
    mock = unittest.mock.MagicMock()
    mock.status = DatabaseMigrationStatus.PENDING
    mock.script = None
    return mock


@pytest.fixture
def container_mock():
    """Create a mock instance for the Container."""
    mock = unittest.mock.MagicMock()
    pull_result = unittest.mock.MagicMock()
    pull_result.read.return_value = str(DEFAULT_LAYER["services"]).replace("'", '"')
    mock.pull.return_value = pull_result
    return mock


def _build_harness(meta=None):
    """Create a harness instance with the specified metadata."""
    harness = Harness(DjangoCharm, meta=meta)
    harness.set_leader()
    root = harness.get_filesystem_root(DJANGO_CONTAINER_NAME)
    (root / "django/app").mkdir(parents=True)
    harness.set_can_connect(DJANGO_CONTAINER_NAME, True)

    def check_config_handler(_):
        """Handle the gunicorn check config command."""
        config_file = root / "django/gunicorn.conf.py"
        if config_file.is_file():
            return ops.testing.ExecResult(0)
        return ops.testing.ExecResult(1)

    check_config_command = [
        "/bin/python3",
        "-m",
        "gunicorn",
        "-c",
        "/django/gunicorn.conf.py",
        "django_app.wsgi:application",
        "-k",
        "sync",
        "--check-config",
    ]
    harness.handle_exec(
        DJANGO_CONTAINER_NAME,
        check_config_command,
        handler=check_config_handler,
    )

    gevent_check_config_command = [
        "/bin/python3",
        "-m",
        "gunicorn",
        "-c",
        "/django/gunicorn.conf.py",
        "django_app.wsgi:application",
        "-k",
        "gevent",
        "--check-config",
    ]
    harness.handle_exec(
        DJANGO_CONTAINER_NAME,
        gevent_check_config_command,
        handler=check_config_handler,
    )

    return harness
