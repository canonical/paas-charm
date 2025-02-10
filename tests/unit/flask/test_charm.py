# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm unit tests."""

# this is a unit test file
# pylint: disable=protected-access

import unittest.mock
from secrets import token_hex

import ops
import pytest
from ops.pebble import ServiceStatus
from ops.testing import Harness

from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm._gunicorn.wsgi_app import WsgiApp
from paas_charm.charm_state import CharmState, IntegrationRequirers
from paas_charm.database_migration import DatabaseMigrationStatus
from paas_charm.flask import Charm

from .constants import (
    DEFAULT_LAYER,
    FLASK_CONTAINER_NAME,
    INTEGRATIONS_RELATION_DATA,
    SAML_APP_RELATION_DATA_EXAMPLE,
)


def test_flask_pebble_layer(harness: Harness) -> None:
    """
    arrange: none
    act: start the flask charm and set flask-app container to be ready.
    assert: flask charm should submit the correct flaks pebble layer to pebble.
    """
    harness.begin()
    container = harness.charm.unit.get_container(FLASK_CONTAINER_NAME)
    # ops.testing framework apply layers by label in lexicographical order...
    container.add_layer("a_layer", DEFAULT_LAYER)
    secret_storage = unittest.mock.MagicMock()
    secret_storage.is_initialized = True
    test_key = "0" * 16
    secret_storage.get_secret_key.return_value = test_key
    charm_state = CharmState.from_charm(
        framework_config=Charm.get_framework_config(harness.charm),
        config=harness.charm.config,
        framework="flask",
        secret_storage=secret_storage,
        integration_requirers=IntegrationRequirers(databases={}),
    )
    webserver_config = WebserverConfig.from_charm_config(harness.charm.config)
    workload_config = create_workload_config(framework_name="flask", unit_name="flask/0")
    webserver = GunicornWebserver(
        webserver_config=webserver_config,
        workload_config=workload_config,
        container=container,
    )
    flask_app = WsgiApp(
        container=container,
        charm_state=charm_state,
        workload_config=workload_config,
        webserver=webserver,
        database_migration=harness.charm._database_migration,
    )
    flask_app.restart()
    plan = container.get_plan()
    flask_layer = plan.to_dict()["services"]["flask"]
    assert flask_layer == {
        "environment": {
            "FLASK_PREFERRED_URL_SCHEME": "HTTPS",
            "FLASK_SECRET_KEY": "0000000000000000",
        },
        "override": "replace",
        "startup": "enabled",
        "command": f"/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app  -k sync",
        "after": ["statsd-exporter"],
        "user": "_daemon_",
    }


def test_rotate_secret_key_action(harness: Harness):
    """
    arrange: none
    act: invoke the rotate-secret-key callback function
    assert: the action should change the secret key value in the relation data and restart the
        flask application with the new secret key.
    """
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.begin_with_initial_hooks()
    action_event = unittest.mock.MagicMock()
    secret_key = harness.get_relation_data(0, harness.charm.app)["flask_secret_key"]
    assert secret_key
    harness.charm._on_rotate_secret_key_action(action_event)
    new_secret_key = harness.get_relation_data(0, harness.charm.app)["flask_secret_key"]
    assert secret_key != new_secret_key


def test_ingress(harness: Harness):
    """
    arrange: Integrate the charm with an ingress provider.
    act: Run all initial hooks.
    assert: The flask service should have the environment variable FLASK_BASE_URL from
        the ingress url relation.
    """
    harness.set_model_name("flask-model")
    harness.add_relation(
        "ingress",
        "nginx-ingress-integrator",
        app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    assert service_env["FLASK_BASE_URL"] == "http://juju.test/"


def test_integrations_wiring(harness: Harness):
    """
    arrange: Prepare a Redis a database, a S3 integration and a SAML integration
    act: Start the flask charm and set flask-app container to be ready.
    assert: The flask service should have environment variables in its plan
        for each of the integrations.
    """
    redis_relation_data = {
        "hostname": "10.1.88.132",
        "port": "6379",
    }
    harness.add_relation("redis", "redis-k8s", unit_data=redis_relation_data)
    postgresql_relation_data = {
        "database": "test-database",
        "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
        "password": "test-password",
        "username": "test-username",
    }
    harness.add_relation("postgresql", "postgresql-k8s", app_data=postgresql_relation_data)
    s3_relation_data = {
        "access-key": token_hex(16),
        "secret-key": token_hex(16),
        "bucket": "flask-bucket",
    }
    harness.add_relation("s3", "s3-integration", app_data=s3_relation_data)
    harness.add_relation("saml", "saml-integrator", app_data=SAML_APP_RELATION_DATA_EXAMPLE)

    harness.set_leader(True)
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()
    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    assert "MYSQL_DB_CONNECT_STRING" not in service_env
    assert service_env["REDIS_DB_CONNECT_STRING"] == "redis://10.1.88.132:6379"
    assert (
        service_env["POSTGRESQL_DB_CONNECT_STRING"]
        == "postgresql://test-username:test-password@test-postgresql:5432/test-database"
    )
    assert service_env["SAML_ENTITY_ID"] == SAML_APP_RELATION_DATA_EXAMPLE["entity_id"]


@pytest.mark.parametrize(
    "rabbitmq_relation_data,expected_env_vars",
    [
        pytest.param(
            {
                "app_data": {
                    "hostname": "rabbitmq-k8s-endpoints.testing.svc.cluster.local",
                    "password": "3m036hhyiDHs",
                },
                "unit_data": {
                    "egress-subnets": "10.152.183.168/32",
                    "ingress-address": "10.152.183.168",
                    "private-address": "10.152.183.168",
                },
            },
            {
                "RABBITMQ_HOSTNAME": "rabbitmq-k8s-endpoints.testing.svc.cluster.local",
                "RABBITMQ_USERNAME": "flask-k8s",
                "RABBITMQ_PASSWORD": "3m036hhyiDHs",
                "RABBITMQ_VHOST": "/",
                "RABBITMQ_CONNECT_STRING": "amqp://flask-k8s:3m036hhyiDHs@rabbitmq-k8s-endpoints.testing.svc.cluster.local:5672/%2F",
            },
            id="rabbitmq-k8s version",
        ),
        pytest.param(
            {
                "app_data": {},
                "unit_data": {
                    "hostname": "10.58.171.158",
                    "password": "LGg6HMJXPF8G3cHMcMg28ZpwSWRfS6hb8s57Jfkt5TW3rtgV5ypZkV8ZY4GcrhW8",
                    "private-address": "10.58.171.158",
                },
            },
            {
                "RABBITMQ_HOSTNAME": "10.58.171.158",
                "RABBITMQ_USERNAME": "flask-k8s",
                "RABBITMQ_PASSWORD": "LGg6HMJXPF8G3cHMcMg28ZpwSWRfS6hb8s57Jfkt5TW3rtgV5ypZkV8ZY4GcrhW8",
                "RABBITMQ_VHOST": "/",
                "RABBITMQ_CONNECT_STRING": "amqp://flask-k8s:LGg6HMJXPF8G3cHMcMg28ZpwSWRfS6hb8s57Jfkt5TW3rtgV5ypZkV8ZY4GcrhW8@10.58.171.158:5672/%2F",
            },
            id="rabbitmq-server version",
        ),
    ],
)
def test_rabbitmq_integration(harness: Harness, rabbitmq_relation_data, expected_env_vars):
    """
    arrange: Prepare a rabbitmq integration (RabbitMQ)
    act: Start the flask charm and set flask-app container to be ready.
    assert: The flask service should have environment variables in its plan
        for each of the integrations.
    """
    harness.add_relation("rabbitmq", "rabbitmq", **rabbitmq_relation_data)
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    for env, env_val in expected_env_vars.items():
        assert env in service_env
        assert service_env[env] == env_val


def test_rabbitmq_integration_with_relation_data_empty(harness: Harness):
    """
    arrange: Prepare a rabbitmq integration (RabbitMQ), with missing data.
    act: Start the flask charm and set flask-app container to be ready.
    assert: The flask service should not have environment variables related to RabbitMQ
    """
    harness.add_relation("rabbitmq", "rabbitmq")
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    for env in service_env.keys():
        assert "RABBITMQ" not in env


def test_rabbitmq_remove_integration(harness: Harness):
    """
    arrange: Prepare a charm with a complete rabbitmq integration (RabbitMQ).
    act: Remove the relation.
    assert: The relation should not have the env variables related to RabbitMQ.
    """
    relation_id = harness.add_relation(
        "rabbitmq", "rabbitmq", app_data={"hostname": "example.com", "password": token_hex(16)}
    )
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.begin_with_initial_hooks()
    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    assert "RABBITMQ_HOSTNAME" in service_env

    harness.remove_relation(relation_id)

    service_env = container.get_plan().services["flask"].environment
    assert "RABBITMQ_HOSTNAME" not in service_env


@pytest.mark.parametrize(
    "integrate_to,required_integrations",
    [
        pytest.param(["saml"], ["s3"], id="s3 fails"),
        pytest.param(["redis", "s3"], ["mysql", "postgresql"], id="postgresql and mysql fail"),
        pytest.param(
            [],
            ["mysql", "postgresql", "mongodb", "s3", "redis", "saml", "rabbitmq"],
            id="all fail",
        ),
    ],
)
def test_missing_integrations(harness: Harness, integrate_to, required_integrations):
    """
    arrange: Prepare the harness. Instantiate the charm with some required integrations.
    act: Integrate with some integrations (but not all the required ones).
    assert: The charm should be blocked. The message should list only the required integrations
         that are missing.
    """
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)
    for integration in required_integrations:
        harness.framework.meta.requires[integration].optional = False
    harness.begin_with_initial_hooks()
    assert isinstance(harness.model.unit.status, ops.model.BlockedStatus)

    for integration in integrate_to:
        harness.add_relation(integration, integration, **INTEGRATIONS_RELATION_DATA[integration])

    integrations_that_should_fail = set(required_integrations) - set(integrate_to)
    integrations_that_should_not_fail = (
        set(INTEGRATIONS_RELATION_DATA.keys()) - integrations_that_should_fail
    )
    assert isinstance(harness.model.unit.status, ops.model.BlockedStatus)
    for integration in integrations_that_should_fail:
        assert integration in harness.model.unit.status.message
    for integration in integrations_that_should_not_fail:
        assert integration not in harness.model.unit.status.message


def test_missing_required_integration_stops_all_and_sets_migration_to_pending(harness: Harness):
    """
    arrange: Prepare the harness. Instantiate the charm with all the required integrations
        so it is active. Include a migrate.sh file so migrations run.
    act: Remove one required integration.
    assert: The charm should be blocked. All services should be stopped and the
        database migration pending.
    """
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    root = harness.get_filesystem_root(container)
    (root / "flask/app/migrate.sh").touch()
    harness.handle_exec(container, [], result=0)
    container.add_layer("a_layer", DEFAULT_LAYER)
    harness.framework.meta.requires["s3"].optional = False
    relation_id = harness.add_relation("s3", "s3", **INTEGRATIONS_RELATION_DATA["s3"])
    harness.begin_with_initial_hooks()
    assert isinstance(harness.model.unit.status, ops.model.ActiveStatus)
    for name, service in container.get_services().items():
        assert service.current == ServiceStatus.ACTIVE
    assert harness._charm._database_migration.get_status() == DatabaseMigrationStatus.COMPLETED

    harness.remove_relation(relation_id)

    assert isinstance(harness.model.unit.status, ops.model.BlockedStatus)
    for name, service in container.get_services().items():
        assert service.current == ServiceStatus.INACTIVE
    assert harness._charm._database_migration.get_status() == DatabaseMigrationStatus.PENDING


def test_invalid_config(harness: Harness):
    """
    arrange: Prepare the harness. Instantiate the charm.
    act: update the config to an invalid env variables (must be more than 1 chars).
    assert: The flask service is blocked with invalid configuration.
    """
    harness.begin()
    harness.update_config({"flask-env": ""})
    assert harness.model.unit.status == ops.BlockedStatus("invalid configuration: flask-env")


def test_invalid_integration(harness: Harness):
    """
    arrange: Prepare the harness. Instantiate the charm.
    act: Integrate with an invalid integration.
    assert: The flask service is blocked because the integration data is wrong.
    """
    s3_relation_data = {
        # Missing required access-key and secret-key.
        "bucket": "flask-bucket",
    }
    harness.add_relation("s3", "s3-integration", app_data=s3_relation_data)
    harness.begin_with_initial_hooks()
    assert isinstance(harness.model.unit.status, ops.BlockedStatus)
    assert "S3" in str(harness.model.unit.status.message)
