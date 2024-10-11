# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Django charm unit tests."""

# this is a unit test file
# pylint: disable=protected-access

import unittest.mock

import ops
import pytest
from ops.testing import ExecArgs, ExecResult, Harness

from examples.django.charm.src.charm import DjangoCharm
from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm._gunicorn.wsgi_app import WsgiApp
from paas_charm.charm_state import CharmState

from .constants import DEFAULT_LAYER

TEST_DJANGO_CONFIG_PARAMS = [
    pytest.param({}, {"DJANGO_SECRET_KEY": "test", "DJANGO_ALLOWED_HOSTS": "[]"}, id="default"),
    pytest.param(
        {"django-allowed-hosts": "test.local"},
        {"DJANGO_SECRET_KEY": "test", "DJANGO_ALLOWED_HOSTS": '["test.local"]'},
        id="allowed-hosts",
    ),
    pytest.param(
        {"django-debug": True},
        {"DJANGO_SECRET_KEY": "test", "DJANGO_ALLOWED_HOSTS": "[]", "DJANGO_DEBUG": "true"},
        id="debug",
    ),
    pytest.param(
        {"django-secret-key": "foobar"},
        {"DJANGO_SECRET_KEY": "foobar", "DJANGO_ALLOWED_HOSTS": "[]"},
        id="secret-key",
    ),
]


@pytest.mark.parametrize("config, env", TEST_DJANGO_CONFIG_PARAMS)
def test_django_config(harness: Harness, config: dict, env: dict) -> None:
    """
    arrange: none
    act: start the django charm and set django-app container to be ready.
    assert: django charm should submit the correct pebble layer to pebble.
    """
    harness.begin()
    container = harness.charm.unit.get_container("django-app")
    # ops.testing framework apply layers by label in lexicographical order...
    container.add_layer("a_layer", DEFAULT_LAYER)
    secret_storage = unittest.mock.MagicMock()
    secret_storage.is_secret_storage_ready = True
    secret_storage.get_secret_key.return_value = "test"
    harness.update_config(config)
    charm_state = CharmState.from_charm(
        config=harness.charm.config,
        framework="django",
        framework_config=harness.charm.get_framework_config(),
        secret_storage=secret_storage,
        database_requirers={},
    )
    webserver_config = WebserverConfig.from_charm_config(harness.charm.config)
    workload_config = create_workload_config(framework_name="django", unit_name="django/0")
    webserver = GunicornWebserver(
        webserver_config=webserver_config,
        workload_config=workload_config,
        container=container,
    )
    django_app = WsgiApp(
        container=harness.charm.unit.get_container("django-app"),
        charm_state=charm_state,
        workload_config=workload_config,
        webserver=webserver,
        database_migration=harness.charm._database_migration,
    )
    django_app.restart()
    plan = container.get_plan()
    django_layer = plan.to_dict()["services"]["django"]
    assert django_layer == {
        "environment": env,
        "override": "replace",
        "startup": "enabled",
        "command": "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application",
        "after": ["statsd-exporter"],
        "user": "_daemon_",
    }


def test_django_create_super_user(harness: Harness) -> None:
    """
    arrange: Start the Django charm. Mock the Django command (pebble exec) to create a superuser.
    act: Run action create superuser.
    assert: The action is called with the right arguments, returning a password for the user.
    """
    postgresql_relation_data = {
        "database": "test-database",
        "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
        "password": "test-password",
        "username": "test-username",
    }
    harness.add_relation("postgresql", "postgresql-k8s", app_data=postgresql_relation_data)
    container = harness.model.unit.get_container("django-app")
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.begin_with_initial_hooks()

    password = None

    def handler(args: ExecArgs) -> None | ExecResult:
        nonlocal password
        assert args.command == ["python3", "manage.py", "createsuperuser", "--noinput"]
        assert args.environment["DJANGO_SUPERUSER_USERNAME"] == "admin"
        assert args.environment["DJANGO_SUPERUSER_EMAIL"] == "admin@example.com"
        assert "DJANGO_SECRET_KEY" in args.environment
        password = args.environment["DJANGO_SUPERUSER_PASSWORD"]
        return ExecResult(stdout="OK")

    harness.handle_exec(
        container, ["python3", "manage.py", "createsuperuser", "--noinput"], handler=handler
    )

    output = harness.run_action(
        "create-superuser", params={"username": "admin", "email": "admin@example.com"}
    )
    assert "password" in output.results
    assert output.results["password"] == password


def test_required_database_integration(harness_no_integrations: Harness):
    """
    arrange: Start the Django charm with no integrations specified in the charm.
    act: Start the django charm and set django-app container to be ready.
    assert: The charm should be blocked, as Django requires a database to work.
    """
    harness = harness_no_integrations
    container = harness.model.unit.get_container("django-app")
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()
    assert harness.model.unit.status == ops.BlockedStatus(
        "Django requires a database integration to work"
    )
