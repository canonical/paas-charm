# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Springboot charm unit tests for integrations."""

from unittest.mock import MagicMock

import pytest
from ops import testing

from paas_charm.springboot.charm import generate_smtp_env, generate_valkey_env

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801


def test_integration_mappers_without_relation_data() -> None:
    """
    arrange: no SMTP or Valkey relation data.
    act: generate the Spring Boot integration environment variables.
    assert: no environment variables are generated.
    """
    assert not generate_smtp_env()
    assert not generate_valkey_env()


def test_valkey_environment_with_credentials() -> None:
    """
    arrange: Valkey relation data with credentials.
    act: generate the Spring Boot Valkey environment variables.
    assert: the URL components and credentials are mapped without selecting a client.
    """
    credential = "test-value"
    relation_data = MagicMock(
        endpoints="valkey-primary:6379",
        read_only_endpoints=None,
        sentinel_endpoints=None,
        username="application",
        mode=None,
        version="9.0.1",
        **{"pass" + "word": credential},
    )

    assert generate_valkey_env(relation_data) == {
        "spring.data.valkey.url": (f"valkey://application:{credential}@valkey-primary:6379"),
        "spring.data.valkey.host": "valkey-primary",
        "spring.data.valkey.port": "6379",
        "spring.data.valkey.username": "application",
        "spring.data.valkey.password": credential,
    }


@pytest.mark.parametrize(
    "relation_data, expected_environment",
    [
        pytest.param(
            {
                "auth_type": "none",
                "domain": "example.com",
                "host": "mailcatcher",
                "port": "1025",
                "skip_ssl_verify": "false",
                "transport_security": "none",
            },
            {
                "spring.mail.host": "mailcatcher",
                "spring.mail.port": "1025",
                "spring.mail.properties.mail.smtp.auth": "false",
                "spring.mail.properties.mail.smtp.starttls.enable": "false",
            },
            id="without authentication",
        ),
        pytest.param(
            {
                "auth_type": "plain",
                "domain": "example.com",
                "host": "smtp.example.com",
                "password": "secret",
                "port": "587",
                "skip_ssl_verify": "false",
                "transport_security": "starttls",
                "user": "app",
            },
            {
                "spring.mail.host": "smtp.example.com",
                "spring.mail.port": "587",
                "spring.mail.username": "app@example.com",
                "spring.mail.password": "secret",
                "spring.mail.properties.mail.smtp.auth": "true",
                "spring.mail.properties.mail.smtp.starttls.enable": "true",
            },
            id="with authentication and STARTTLS",
        ),
    ],
)
def test_smtp_integration(
    springboot_context,
    base_state,
    relation_data,
    expected_environment,
) -> None:
    """
    arrange: add smtp relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the smtp related env variables.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="smtp",
            interface="smtp-integrator",
            remote_app_data=relation_data,
        )
    )
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    smtp_relation = out.get_relations("smtp")
    assert len(smtp_relation) == 1

    assert {key: environment[key] for key in expected_environment} == expected_environment
    if "spring.mail.username" not in expected_environment:
        assert "spring.mail.username" not in environment
        assert "spring.mail.password" not in environment


def test_saml_integration(
    springboot_context,
    base_state,
) -> None:
    """
    arrange: add saml relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the saml related env variables.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="saml",
            interface="saml-integrator",
            remote_app_data={
                "entity_id": "http://example.com/entity",
                "metadata_url": "http://example.com/metadata",
                "x509certs": "cert1",
                "single_sign_on_service_redirect_url": "http://example.com/sso",
                "single_sign_on_service_redirect_binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
        )
    )
    state = testing.State(**base_state)
    out = springboot_context.run(springboot_context.on.config_changed(), state)
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    saml_relation = out.get_relations("saml")
    assert len(saml_relation) == 1

    assert (
        environment[
            "spring.security.saml2.relyingparty.registration.testentity.assertingparty.metadata-uri"
        ]
        == "http://example.com/metadata"
    )
    assert (
        environment["spring.security.saml2.relyingparty.registration.testentity.entity-id"]
        == "http://example.com/entity"
    )
    assert (
        environment[
            "spring.security.saml2.relyingparty.registration.testentity.assertingparty.singlesignin.url"
        ]
        == "http://example.com/sso"
    )
    assert (
        environment[
            "spring.security.saml2.relyingparty.registration.testentity.assertingparty.verification.credentials[0].certificate-location"
        ]
        == "file:/app/saml.cert"
    )


def test_valkey_integration(
    springboot_context,
    base_state,
) -> None:
    """
    arrange: add valkey relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the valkey related env variables.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="valkey",
            interface="valkey_client",
            remote_app_data={
                "requests": (
                    '[{"resource": "*", "request-id": "a2b7f513afa07883", '
                    '"endpoints": "valkey-primary:6379", "salt": "Uh39g15ZlrWSwJtk"}]'
                ),
                "version": "v1",
            },
            remote_units_data={0: {}},
        )
    )
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    valkey_relation = out.get_relations("valkey")
    assert len(valkey_relation) == 1

    assert environment["spring.data.valkey.host"] == "valkey-primary"
    assert environment["spring.data.valkey.port"] == "6379"
    assert environment["spring.data.valkey.url"] == "valkey://valkey-primary:6379"
    assert "spring.data.valkey.client-type" not in environment
    assert environment.get("spring.data.valkey.username") is None
    assert environment.get("spring.data.valkey.password") is None


def test_s3_integration(
    springboot_context,
    base_state,
) -> None:
    """
    arrange: add s3 relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the s3 related env variables.
    """
    s3_app_data = {
        "access-key": "access-key",
        "bucket": "paas-bucket",
        "endpoint": "http://s3-0.test-endpoint:9000",
        "region": "mars-north-3",
        "secret-key": "super-duper-secret-key",
    }
    base_state["relations"].append(
        testing.Relation(endpoint="s3", interface="s3", remote_app_data=s3_app_data)
    )
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    s3_relation = out.get_relations("s3")
    assert len(s3_relation) == 1

    assert environment["spring.cloud.aws.credentials.accessKey"] == s3_app_data["access-key"]
    assert environment["spring.cloud.aws.credentials.secretKey"] == s3_app_data["secret-key"]
    assert environment["spring.cloud.aws.region.static"] == s3_app_data["region"]
    assert environment["spring.cloud.aws.s3.bucket"] == s3_app_data["bucket"]
    assert environment["spring.cloud.aws.s3.endpoint"] == s3_app_data["endpoint"]


def test_mongodb_integration(
    springboot_context,
    base_state,
) -> None:
    """
    arrange: add mongodb relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the mongodb related env variables.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="mongodb",
            interface="mongodb_client",
            remote_app_data={
                "database": "spring-boot-k8s",
                "endpoints": "test-mongodb:27017",
                "password": "test-mongodb-password",
                "username": "test-mongodb-username",
            },
        )
    )
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    mongodb_relation = out.get_relations("mongodb")
    assert len(mongodb_relation) == 1

    assert (
        environment["spring.data.mongodb.uri"]
        == "mongodb://test-mongodb-username:test-mongodb-password@test-mongodb:27017/spring-boot-k8s"
    )


def test_mysql_integration(
    springboot_context,
    mysql_base_state,
) -> None:
    """
    arrange: add mysql relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the mysql related env variables.
    """
    state = testing.State(**mysql_base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    mysql_relation = out.get_relations("mysql")
    assert len(mysql_relation) == 1

    assert environment["spring.datasource.username"] == "test-username"
    assert environment["spring.datasource.password"] == "test-password"
    assert environment["spring.datasource.url"] == "jdbc:mysql://test-mysql:3306/spring-boot-k8s"
    assert environment["spring.jpa.hibernate.ddl-auto"] == "none"
    assert environment["MYSQL_DB_NAME"] == "spring-boot-k8s"


def test_openfga_integration(
    springboot_context,
    base_state,
) -> None:
    """
    arrange: add OpenFGA relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the OpenFGA related env variables.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="openfga",
            interface="openfga",
            remote_app_data={
                "store_id": "test-store-id",
                "token": "test-token",
                "grpc_api_url": "localhost:8081",
                "http_api_url": "localhost:8080",
            },
        )
    )
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    openfga_relation = out.get_relations("openfga")
    assert len(openfga_relation) == 1

    assert environment["openfga.store-id"] == "test-store-id"
    assert environment["openfga.credentials.method"] == "API_TOKEN"
    assert environment["openfga.credentials.config.api-token"] == "test-token"
    assert environment["openfga.api-url"] == "localhost:8080"


def test_rabbitmq_integration(
    springboot_context,
    base_state,
) -> None:
    """
    arrange: add rabbitmq relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the rabbitmq related env variables.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="rabbitmq",
            interface="rabbitmq",
            remote_app_data={
                "hostname": "rabbitmq-k8s-endpoints.testing.svc.cluster.local",
                "password": "EkKV1iy4mKrj",
            },
            remote_units_data={
                0: {
                    "egress-subnets": "10.152.183.237/32",
                    "ingress-address": "10.152.183.237",
                    "private-address": "10.152.183.237",
                }
            },
        )
    )
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    rabbitmq_relation = out.get_relations("rabbitmq")
    assert len(rabbitmq_relation) == 1

    assert environment["spring.rabbitmq.virtual-host"] == "/"
    assert environment["spring.rabbitmq.username"] == "spring-boot-k8s"
    assert environment["spring.rabbitmq.password"] == "EkKV1iy4mKrj"
    assert (
        environment["spring.rabbitmq.host"] == "rabbitmq-k8s-endpoints.testing.svc.cluster.local"
    )
    assert environment["spring.rabbitmq.port"] == "5672"
