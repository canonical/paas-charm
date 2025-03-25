# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Django charm unit tests."""

# this is a unit test file
# pylint: disable=protected-access

import unittest.mock

import ops
import pytest
from ops.testing import ExecArgs, ExecResult, Harness

from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm._gunicorn.wsgi_app import WsgiApp
from paas_charm.charm_state import CharmState, IntegrationRequirers

from .constants import DEFAULT_LAYER, DJANGO_CONTAINER_NAME

TEST_DJANGO_CONFIG_PARAMS = [
    pytest.param(
        {},
        {"DJANGO_SECRET_KEY": "test", "DJANGO_ALLOWED_HOSTS": '["django-k8s.none"]'},
        id="default",
    ),
    pytest.param(
        {"django-allowed-hosts": "test.local"},
        {"DJANGO_SECRET_KEY": "test", "DJANGO_ALLOWED_HOSTS": '["test.local", "django-k8s.none"]'},
        id="allowed-hosts",
    ),
    pytest.param(
        {"django-debug": True},
        {
            "DJANGO_SECRET_KEY": "test",
            "DJANGO_ALLOWED_HOSTS": '["django-k8s.none"]',
            "DJANGO_DEBUG": "true",
        },
        id="debug",
    ),
    pytest.param(
        {"django-secret-key": "foobar"},
        {
            "DJANGO_SECRET_KEY": "foobar",
            "DJANGO_ALLOWED_HOSTS": '["django-k8s.none"]',
        },
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
    container = harness.charm.unit.get_container(DJANGO_CONTAINER_NAME)
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
        integration_requirers=IntegrationRequirers(databases={}),
    )
    webserver_config = WebserverConfig.from_charm_config(harness.charm.config)
    workload_config = create_workload_config(framework_name="django", unit_name="django/0")
    webserver = GunicornWebserver(
        webserver_config=webserver_config,
        workload_config=workload_config,
        container=container,
    )
    django_app = WsgiApp(
        container=harness.charm.unit.get_container(DJANGO_CONTAINER_NAME),
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
        "command": "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application -k [ sync ]",
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
    container = harness.model.unit.get_container(DJANGO_CONTAINER_NAME)
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
    container = harness.model.unit.get_container(DJANGO_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()
    assert harness.model.unit.status == ops.BlockedStatus(
        "Django requires a database integration to work"
    )


@pytest.mark.parametrize("config, env", TEST_DJANGO_CONFIG_PARAMS)
def test_django_async_config(harness: Harness, config: dict, env: dict) -> None:
    """
    arrange: None
    act: Start the django charm and set django-app container to be ready.
    assert: Django charm should submit the correct pebble layer to pebble.
    """
    harness.begin()
    container = harness.charm.unit.get_container(DJANGO_CONTAINER_NAME)
    # ops.testing framework apply layers by label in lexicographical order...
    container.add_layer("a_layer", DEFAULT_LAYER)
    secret_storage = unittest.mock.MagicMock()
    secret_storage.is_secret_storage_ready = True
    secret_storage.get_secret_key.return_value = "test"
    config["webserver-worker-class"] = "gevent"
    harness.update_config(config)
    charm_state = CharmState.from_charm(
        config=harness.charm.config,
        framework="django",
        framework_config=harness.charm.get_framework_config(),
        secret_storage=secret_storage,
        integration_requirers=IntegrationRequirers(databases={}),
    )
    webserver_config = WebserverConfig.from_charm_config(harness.charm.config)
    workload_config = create_workload_config(framework_name="django", unit_name="django/0")
    webserver = GunicornWebserver(
        webserver_config=webserver_config,
        workload_config=workload_config,
        container=container,
    )
    django_app = WsgiApp(
        container=harness.charm.unit.get_container(DJANGO_CONTAINER_NAME),
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
        "command": "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application -k [ gevent ]",
        "after": ["statsd-exporter"],
        "user": "_daemon_",
    }


def test_allowed_hosts_base_hostname_updates_correctly(harness: Harness):
    """
    arrange: Deploy a Django charm without an ingress integration
    act: Add a new ingress integration
    assert: The allowed hosts env var should match the url of the ingress integration
    act: Update the url in the ingress integration
    assert: The allowed hosts env var should match the new url of the ingress integration
    """
    postgresql_relation_data = {
        "database": "test-database",
        "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
        "password": "test-password",
        "username": "test-username",
    }
    harness.add_relation("postgresql", "postgresql-k8s", app_data=postgresql_relation_data)
    container = harness.model.unit.get_container(DJANGO_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.set_model_name("flask-model")
    harness.begin_with_initial_hooks()

    # The initial allowed hosts matches the k8s service name.
    plan = container.get_plan()
    env = plan.to_dict()["services"]["django"]["environment"]
    assert env["DJANGO_ALLOWED_HOSTS"] == '["django-k8s.flask-model"]'

    # Add a relation and the allowed hosts should be updated to the ingress url
    harness.add_network("10.0.0.10", endpoint="ingress")
    relation_id = harness.add_relation(
        "ingress",
        "nginx-ingress-integrator",
        app_data={"ingress": '{"url": "http://oldjuju.test/"}'},
    )

    plan = container.get_plan()
    env = plan.to_dict()["services"]["django"]["environment"]
    assert env["DJANGO_ALLOWED_HOSTS"] == '["oldjuju.test"]'

    # Updating the ingress url to a new url should update the allowed hosts.
    harness.update_relation_data(
        relation_id,
        app_or_unit="nginx-ingress-integrator",
        key_values={"ingress": '{"url": "http://newjuju.test/"}'},
    )

    plan = container.get_plan()
    env = plan.to_dict()["services"]["django"]["environment"]
    assert env["DJANGO_ALLOWED_HOSTS"] == '["newjuju.test"]'
