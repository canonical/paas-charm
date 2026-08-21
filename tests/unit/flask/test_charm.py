# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm Scenario tests."""

from secrets import token_hex

import pytest
from ops import testing

from .constants import (
    INTEGRATIONS_RELATION_DATA,
    SAML_APP_RELATION_DATA_EXAMPLE,
)


def _relation(endpoint: str, relation_data: dict) -> testing.Relation:
    """Build an integration relation from the shared relation data shape."""
    return testing.Relation(
        endpoint=endpoint,
        interface={
            "postgresql": "postgresql_client",
            "mysql": "mysql_client",
            "mongodb": "mongodb_client",
            "redis": "redis",
            "s3": "s3",
            "saml": "saml",
        }.get(endpoint, endpoint),
        remote_app_data=relation_data.get("app_data", {}),
        remote_units_data={0: relation_data.get("unit_data", {})},
    )


def test_flask_pebble_layer(flask_context, base_state, container_name: str) -> None:
    """
    arrange: prepare a leader Flask unit with its peer relation and workload container.
    act: reconcile the charm on config-changed.
    assert: the charm submits the exact Flask Pebble service definition.
    """
    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    app_secret = out.get_secret(label="flask-secret-key").tracked_content["value"]
    assert out.unit_status == testing.ActiveStatus()
    assert out.get_container(container_name).plan.services["flask"].to_dict() == {
        "environment": {
            "FLASK_BASE_URL": "http://flask-k8s.test-model:8000",
            "FLASK_METRICS_PATH": "/metrics",
            "FLASK_METRICS_PORT": "9102",
            "FLASK_OIDC_REDIRECT_PATH": "/callback",
            "FLASK_OIDC_SCOPES": "openid profile email",
            "FLASK_PREFERRED_URL_SCHEME": "HTTPS",
            "FLASK_SECRET_KEY": app_secret,
        },
        "override": "replace",
        "startup": "enabled",
        "command": "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app -k [ sync ]",
        "after": ["statsd-exporter"],
        "user": "_daemon_",
    }


def test_rotate_secret_key_action(flask_context, base_state, container_name: str) -> None:
    """
    arrange: prepare an initialized leader Flask unit.
    act: run the rotate-secret-key action.
    assert: the secret store and the workload environment contain a new key and the action
        succeeds.
    """
    state = testing.State(**base_state)
    old_secret = state.get_secret(label="flask-secret-key").tracked_content["value"]

    out = flask_context.run(
        flask_context.on.action("rotate-secret-key"),
        state,
    )

    new_secret = out.get_secret(label="flask-secret-key").tracked_content["value"]
    assert new_secret
    assert new_secret != old_secret
    assert flask_context.action_results == {"status": "success"}
    service = out.get_container(container_name).plan.services["flask"]
    assert service.environment["FLASK_SECRET_KEY"] == new_secret


def test_ingress(flask_context, base_state, container_name: str) -> None:
    """
    arrange: integrate the Flask charm with an ingress provider.
    act: reconcile the relation.
    assert: the workload base URL is the related ingress URL.
    """
    ingress = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["model"] = testing.Model(name="flask-model")
    base_state["relations"].append(ingress)

    out = flask_context.run(
        flask_context.on.relation_changed(ingress),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    service = out.get_container(container_name).plan.services["flask"]
    assert service.environment["FLASK_BASE_URL"] == "http://juju.test/"


def test_integrations_wiring(flask_context, base_state, container_name: str) -> None:
    """
    arrange: relate Redis, PostgreSQL, S3, and SAML integrations.
    act: reconcile the charm.
    assert: the workload receives the exact integration environment values.
    """
    relations = [
        _relation("redis", INTEGRATIONS_RELATION_DATA["redis"]),
        _relation("postgresql", INTEGRATIONS_RELATION_DATA["postgresql"]),
        _relation("s3", INTEGRATIONS_RELATION_DATA["s3"]),
        _relation("saml", INTEGRATIONS_RELATION_DATA["saml"]),
    ]
    base_state["relations"].extend(relations)

    out = flask_context.run(
        flask_context.on.relation_changed(relations[0], remote_unit=0),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["flask"].environment
    assert "MYSQL_DB_CONNECT_STRING" not in environment
    assert environment["REDIS_DB_CONNECT_STRING"] == "redis://10.1.88.132:6379"
    assert (
        environment["POSTGRESQL_DB_CONNECT_STRING"]
        == "postgresql://test-username:test-password@test-postgresql:5432/test-database"
    )
    assert environment["S3_BUCKET"] == "flask-bucket"
    assert environment["SAML_ENTITY_ID"] == SAML_APP_RELATION_DATA_EXAMPLE["entity_id"]


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
            },
            id="rabbitmq-server version",
        ),
    ],
)
def test_rabbitmq_integration(
    flask_context,
    base_state,
    container_name: str,
    rabbitmq_relation_data: dict,
    expected_env_vars: dict,
) -> None:
    """
    arrange: relate a RabbitMQ provider using either supported data shape.
    act: reconcile the relation.
    assert: every RabbitMQ workload environment value is exact.
    """
    relation = _relation("rabbitmq", rabbitmq_relation_data)
    base_state["relations"].append(relation)

    out = flask_context.run(
        flask_context.on.relation_changed(relation, remote_unit=0),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["flask"].environment
    assert {key: environment[key] for key in expected_env_vars} == expected_env_vars
    relation_data = rabbitmq_relation_data["app_data"] or rabbitmq_relation_data["unit_data"]
    assert environment["RABBITMQ_CONNECT_STRING"] == (
        f"amqp://flask-k8s:{relation_data['password']}@" f"{relation_data['hostname']}:5672/%2F"
    )


def test_rabbitmq_integration_with_relation_data_empty(
    flask_context,
    base_state,
    container_name: str,
) -> None:
    """
    arrange: relate RabbitMQ without connection data.
    act: reconcile the relation.
    assert: the workload has no RabbitMQ environment values.
    """
    relation = _relation("rabbitmq", {})
    base_state["relations"].append(relation)

    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["flask"].environment
    assert not {key for key in environment if key.startswith("RABBITMQ_")}


def test_rabbitmq_remove_integration(
    flask_context,
    base_state,
    container_name: str,
) -> None:
    """
    arrange: reconcile a complete RabbitMQ relation.
    act: reconcile the output state after removing that relation.
    assert: RabbitMQ environment values are removed from the workload plan.
    """
    relation = _relation(
        "rabbitmq",
        {"app_data": {"hostname": "example.com", "password": token_hex(16)}},
    )
    base_state["relations"].append(relation)
    out = flask_context.run(
        flask_context.on.relation_changed(relation, remote_unit=0),
        testing.State(**base_state),
    )
    assert "RABBITMQ_HOSTNAME" in (
        out.get_container(container_name).plan.services["flask"].environment
    )

    out = flask_context.run(
        flask_context.on.relation_broken(relation),
        out,
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["flask"].environment
    assert not {key for key in environment if key.startswith("RABBITMQ_")}


@pytest.mark.parametrize(
    "integrate_to,required_integrations,expected_message",
    [
        pytest.param(["saml"], ["s3"], "missing integrations: s3", id="s3 fails"),
        pytest.param(
            ["redis", "s3"],
            ["mysql", "postgresql"],
            "missing integrations: mysql, postgresql",
            id="postgresql and mysql fail",
        ),
        pytest.param(
            [],
            ["mysql", "postgresql", "mongodb", "s3", "redis", "saml", "rabbitmq"],
            "missing integrations: mongodb, mysql, postgresql, rabbitmq, redis, s3, saml",
            id="all fail",
        ),
    ],
)
def test_missing_integrations(
    flask_context,
    base_state,
    integrate_to: list[str],
    required_integrations: list[str],
    expected_message: str,
) -> None:
    """
    arrange: mark selected integrations as required and relate only a subset.
    act: reconcile the incomplete state.
    assert: status lists every and only missing required integration in stable order.
    """
    for integration in required_integrations:
        flask_context.charm_spec.meta["requires"][integration]["optional"] = False
    base_state["relations"].extend(
        _relation(integration, INTEGRATIONS_RELATION_DATA[integration])
        for integration in integrate_to
    )

    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.BlockedStatus(expected_message)


def test_invalid_config(flask_context, base_state) -> None:
    """
    arrange: configure an empty Flask environment value.
    act: reconcile the charm.
    assert: the unit is blocked with the exact invalid-option message.
    """
    state = testing.State(**{**base_state, "config": {"flask-env": ""}})

    out = flask_context.run(flask_context.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus("        invalid options: flask-env")


def test_invalid_integration(flask_context, base_state) -> None:
    """
    arrange: relate S3 data missing its required access and secret keys.
    act: reconcile the relation.
    assert: the charm reports the invalid S3 relation data.
    """
    relation = testing.Relation(
        endpoint="s3",
        interface="s3",
        remote_app_data={"bucket": "flask-bucket"},
    )
    base_state["relations"].append(relation)

    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.BlockedStatus("Invalid s3 relation data.")
