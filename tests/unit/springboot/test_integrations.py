# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Springboot charm unit tests for integrations."""

import dataclasses
import json
from unittest.mock import MagicMock

import pytest
import yaml
from ops import testing

from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.exceptions import PaasConfigError
from paas_charm.opensearch import PaaSOpenSearchRelationData
from paas_charm.springboot.charm import (
    SpringOpenSearchRelation,
    SpringValkeyRelation,
    SpringSmtpRelation,
    generate_smtp_env,
)

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

OPENSEARCH_ENDPOINTS = "10.1.1.1:9200,10.1.1.2:9200"
OPENSEARCH_TLS_CA = (
    "-----BEGIN CERTIFICATE-----\nTHE INTERMEDIATE CA CERTIFICATE\n-----END CERTIFICATE-----\n"
    "-----BEGIN CERTIFICATE-----\nTHE ROOT CA CERTIFICATE\n-----END CERTIFICATE-----"
)
OPENSEARCH_SPRING_ENVIRONMENT = {
    "opensearch.uris": "https://10.1.1.1:9200,https://10.1.1.2:9200",
    "opensearch.username": "opensearch-client_7",
    "opensearch.password": "test-opensearch-password",
    "opensearch.restclient.ssl.bundle": "opensearch",
    "spring.ssl.bundle.pem.opensearch.truststore.certificate": OPENSEARCH_TLS_CA,
}


def _add_opensearch_secrets(base_state: dict) -> dict[str, str]:
    """Add the secrets that the OpenSearch provider shares to the state.

    Args:
        base_state: The state to add the secrets to.

    Returns:
        The provider relation data fields that point to the secrets.
    """
    user_secret = testing.Secret(
        tracked_content={"username": "opensearch-client_7", "password": "test-opensearch-password"}
    )
    tls_secret = testing.Secret(tracked_content={"tls": "True", "tls-ca": OPENSEARCH_TLS_CA})
    base_state["secrets"].extend([user_secret, tls_secret])
    return {"secret-user": user_secret.id, "secret-tls": tls_secret.id}


def _opensearch_properties(out: testing.State) -> dict[str, str]:
    """Return the OpenSearch properties and variables of the Spring Boot service.

    Args:
        out: The state after the event.

    Returns:
        The environment entries of the Spring Boot service that mention OpenSearch.
    """
    environment = out.get_container("app").plan.services["spring-boot"].environment
    return {key: value for key, value in environment.items() if "opensearch" in key.lower()}


def test_integration_mappers_without_relation_data() -> None:
    """
    arrange: no SMTP, Valkey or OpenSearch relation data.
    act: generate the Spring Boot integration environment variables.
    assert: no environment variables are generated.
    """
    assert not SpringSmtpRelation._generate_smtp_env()
    assert not SpringValkeyRelation._generate_valkey_env()
    assert not SpringOpenSearchRelation._generate_opensearch_env(None)


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

    assert SpringValkeyRelation._generate_valkey_env(relation_data) == {
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
        == "file:/tmp/paas-charm/saml.cert"
    )
    cert_file = out.get_container("app").get_filesystem(springboot_context) / (
        "tmp/paas-charm/saml.cert"
    )
    assert cert_file.read_text() == "-----BEGIN CERTIFICATE-----\ncert1\n-----END CERTIFICATE-----"


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
    assert "VALKEY_DB_CONNECT_STRING" not in environment
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


def test_opensearch_environment() -> None:
    """
    arrange: OpenSearch relation data with two endpoints, the optional fields and the CA chain.
    act: generate the Spring Boot OpenSearch environment variables.
    assert: every endpoint uses https, the CA chain is trusted through the opensearch SSL bundle,
        and the index and version have no property.
    """
    relation_data = PaaSOpenSearchRelationData.model_validate(
        {
            "endpoints": OPENSEARCH_ENDPOINTS,
            "username": "opensearch-client_7",
            "password": "test-opensearch-password",
            "tls-ca": OPENSEARCH_TLS_CA,
            "index": "spring-boot-k8s",
            "version": "2.19.0",
        }
    )

    assert (
        SpringOpenSearchRelation._generate_opensearch_env(relation_data)
        == OPENSEARCH_SPRING_ENVIRONMENT
    )


@pytest.mark.parametrize(
    "optional_relation_data",
    [
        pytest.param(
            {"index": "spring-boot-k8s", "version": "2.19.0"}, id="with index and version"
        ),
        pytest.param({}, id="without index and version"),
    ],
)
def test_opensearch_integration(
    springboot_context,
    base_state,
    optional_relation_data,
) -> None:
    """
    arrange: add an opensearch relation whose provider shares the credentials and the CA chain
        in Juju secrets, with or without the optional index and version.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should be active with exactly the opensearch related properties.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="opensearch",
            interface="opensearch_client",
            remote_app_data={
                "endpoints": OPENSEARCH_ENDPOINTS,
                **_add_opensearch_secrets(base_state),
                **optional_relation_data,
            },
        )
    )
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)
    assert out.unit_status == testing.ActiveStatus()

    opensearch_relation = out.get_relations("opensearch")
    assert len(opensearch_relation) == 1

    assert _opensearch_properties(out) == OPENSEARCH_SPRING_ENVIRONMENT


def test_opensearch_integration_requests_paas_config_settings(
    springboot_context,
    base_state,
) -> None:
    """
    arrange: add a new opensearch relation to the base state of the leader unit.
    act: run the relation-created event.
    assert: the charm requests the index and the roles set in paas-config.yaml, and no entity.
    """
    relation = testing.Relation(endpoint="opensearch", interface="opensearch_client")
    base_state["relations"].append(relation)
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.relation_created(relation), state)

    local_app_data = out.get_relation(relation.id).local_app_data
    assert local_app_data["index"] == "spring-boot-k8s"
    assert local_app_data["extra-user-roles"] == "admin"
    assert "entity-type" not in local_app_data


def test_opensearch_integration_when_ca_arrives_later(springboot_context, base_state) -> None:
    """
    arrange: add an opensearch relation whose provider has shared everything but the CA chain.
    act: run the config-changed event, then the relation-changed event in which the provider
        shares the CA chain.
    assert: the charm is blocked until the CA chain arrives, then active with the opensearch
        properties.
    """
    secret_fields = _add_opensearch_secrets(base_state)
    shared_before_ca = {
        "endpoints": OPENSEARCH_ENDPOINTS,
        "index": "spring-boot-k8s",
        "version": "2.19.0",
        "secret-user": secret_fields["secret-user"],
    }
    relation = testing.Relation(
        endpoint="opensearch",
        interface="opensearch_client",
        remote_app_data=shared_before_ca,
        # OpenSearchRequires compares the provider data with the copy that it saved during the
        # previous relation-changed event, so only the CA chain is new in the next one.
        local_unit_data={"data": json.dumps(shared_before_ca)},
    )
    base_state["relations"].append(relation)
    out = springboot_context.run(
        springboot_context.on.config_changed(), testing.State(**base_state)
    )
    assert out.unit_status == testing.BlockedStatus(
        "RelationDataError: OpenSearch relation data is not ready"
    )

    relation_with_ca = dataclasses.replace(
        out.get_relation(relation.id),
        remote_app_data={**shared_before_ca, "secret-tls": secret_fields["secret-tls"]},
    )
    other_relations = [other for other in out.relations if other.id != relation.id]
    out = springboot_context.run(
        springboot_context.on.relation_changed(relation_with_ca),
        dataclasses.replace(out, relations=[*other_relations, relation_with_ca]),
    )

    assert out.unit_status == testing.ActiveStatus()
    assert _opensearch_properties(out) == OPENSEARCH_SPRING_ENVIRONMENT


def test_opensearch_integration_when_relation_broken(springboot_context, base_state) -> None:
    """
    arrange: run the config-changed event with a ready opensearch relation.
    act: run the relation-broken event.
    assert: the charm stays active and the opensearch properties are removed.
    """
    relation = testing.Relation(
        endpoint="opensearch",
        interface="opensearch_client",
        remote_app_data={"endpoints": OPENSEARCH_ENDPOINTS, **_add_opensearch_secrets(base_state)},
    )
    base_state["relations"].append(relation)
    out = springboot_context.run(
        springboot_context.on.config_changed(), testing.State(**base_state)
    )
    assert _opensearch_properties(out) == OPENSEARCH_SPRING_ENVIRONMENT

    out = springboot_context.run(
        springboot_context.on.relation_broken(out.get_relation(relation.id)), out
    )

    assert out.unit_status == testing.ActiveStatus()
    assert _opensearch_properties(out) == {}


def test_opensearch_integration_reruns_migrations_when_index_created(
    springboot_context,
    base_state,
    tmp_path,
) -> None:
    """
    arrange: run migrate.sh successfully without the opensearch relation.
    act: add an opensearch relation and run the relation-changed event in which the provider
        shares the credentials, which means that it has created the index.
    assert: migrate.sh runs again, with the opensearch properties.
    """
    command = ["bash", "-eo", "pipefail", "migrate.sh"]
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "migrate.sh").touch()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    container = next(iter(base_state["containers"]))
    base_state["containers"] = {
        dataclasses.replace(
            container,
            # The state directory keeps the migration status between the two events.
            mounts={
                "app": testing.Mount(location="/app", source=app_dir),
                "state": testing.Mount(location="/tmp/paas-charm", source=state_dir),
            },
            execs={testing.Exec(command)},
        )
    }
    secret_fields = _add_opensearch_secrets(base_state)
    out = springboot_context.run(
        springboot_context.on.config_changed(), testing.State(**base_state)
    )
    assert out.unit_status == testing.ActiveStatus()

    relation = testing.Relation(
        endpoint="opensearch",
        interface="opensearch_client",
        remote_app_data={
            "endpoints": OPENSEARCH_ENDPOINTS,
            "index": "spring-boot-k8s",
            **secret_fields,
        },
    )
    out = springboot_context.run(
        springboot_context.on.relation_changed(relation),
        dataclasses.replace(out, relations={*out.relations, relation}),
    )

    assert out.unit_status == testing.ActiveStatus()
    migrations = [
        args for args in springboot_context.exec_history["app"] if args.command == command
    ]
    assert len(migrations) == 2
    assert "opensearch.uris" not in migrations[0].environment
    assert (
        migrations[1].environment["opensearch.uris"]
        == OPENSEARCH_SPRING_ENVIRONMENT["opensearch.uris"]
    )


@pytest.mark.parametrize(
    "paas_config_kwargs",
    [
        pytest.param({"no_paas_config_file": True}, id="no paas-config.yaml"),
        pytest.param(
            {"paas_config_yaml": "port: 8080\n"},
            id="paas-config.yaml without an opensearch section",
        ),
    ],
)
def test_opensearch_integration_without_paas_config_section(
    context_factory,
    base_state,
    paas_config_kwargs,
) -> None:
    """
    arrange: a springboot charm with no paas-config.yaml file, or with one that only sets the
        port to its default, 8080.
    act: run the config-changed event.
    assert: the charm fails to initialize with PaasConfigError.
    """
    context = context_factory(SpringBootCharm, **paas_config_kwargs)

    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**base_state))

    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert "has no opensearch section" in str(exc_info.value.__cause__)


@pytest.mark.parametrize(
    "opensearch_settings, invalid_setting",
    [
        pytest.param(
            {"index": "", "extra-user-roles": "admin"}, "opensearch.index", id="empty index"
        ),
        pytest.param(
            {"index": "spring-boot-k8s", "extra-user-roles": "default"},
            "opensearch.extra-user-roles",
            id="non admin role",
        ),
        pytest.param({"extra-user-roles": "admin"}, "opensearch.index", id="no index"),
        pytest.param({"index": "spring-boot-k8s"}, "opensearch.extra-user-roles", id="no role"),
        pytest.param(
            {"index": "spring-boot-k8s", "extra_user_roles": "admin"},
            "opensearch.extra_user_roles",
            id="extra_user_roles instead of extra-user-roles",
        ),
        pytest.param(
            {"index": "spring-boot-k8s", "extra-user-roles": "admin", "entity-type": "USER"},
            "opensearch.entity-type",
            id="unsupported setting",
        ),
    ],
)
def test_opensearch_integration_with_invalid_paas_config_settings(
    context_factory,
    base_state,
    opensearch_settings,
    invalid_setting,
) -> None:
    """
    arrange: a springboot charm whose paas-config.yaml has invalid opensearch settings.
    act: run the config-changed event.
    assert: the charm fails to initialize with a PaasConfigError naming the invalid setting.
    """
    context = context_factory(
        SpringBootCharm, paas_config_yaml=yaml.safe_dump({"opensearch": opensearch_settings})
    )

    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**base_state))

    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert invalid_setting in str(exc_info.value.__cause__)
