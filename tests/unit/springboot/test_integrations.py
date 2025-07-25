# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Springboot charm unit tests for integrations."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

from secrets import token_hex

from ops import testing

from examples.springboot.charm.src.charm import SpringBootCharm
from tests.unit.conftest import OAUTH_RELATION_DATA_EXAMPLE


def test_smtp_integration(
    base_state,
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
            remote_app_data={
                "auth_type": "none",
                "domain": "example.com",
                "host": "mailcatcher",
                "port": "1025",
                "skip_ssl_verify": "false",
                "transport_security": "none",
            },
        )
    )
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    smtp_relation = out.get_relations("smtp")
    assert len(smtp_relation) == 1

    assert environment["spring.mail.host"] == "mailcatcher"
    assert environment["spring.mail.port"] == 1025
    assert environment["spring.mail.username"] == "None@example.com"
    assert environment["spring.mail.password"] is None
    assert environment["spring.mail.properties.mail.smtp.auth"] == "none"
    assert environment["spring.mail.properties.mail.smtp.starttls.enable"] == "false"


def test_saml_integration(
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
    context = testing.Context(
        charm_type=SpringBootCharm,
    )
    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
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


def test_redis_integration(
    base_state,
) -> None:
    """
    arrange: add redis relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the redis related env variables.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="redis",
            interface="redis",
            remote_app_data={
                "leader-host": "redis-k8s-0.redis-k8s-endpoints.test-model.svc.cluster.local",
            },
            remote_units_data={
                0: {
                    "port": "6379",
                    "username": "",
                    "password": "",
                }
            },
        )
    )
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    redis_relation = out.get_relations("redis")
    assert len(redis_relation) == 1

    assert (
        environment["spring.data.redis.host"]
        == "redis-k8s-0.redis-k8s-endpoints.test-model.svc.cluster.local"
    )
    assert environment["spring.data.redis.port"] == "6379"
    assert (
        environment["spring.data.redis.url"]
        == "redis://redis-k8s-0.redis-k8s-endpoints.test-model.svc.cluster.local:6379"
    )
    assert environment.get("spring.data.redis.username") is None
    assert environment.get("spring.data.redis.password") is None


def test_s3_integration(
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
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    s3_relation = out.get_relations("s3")
    assert len(s3_relation) == 1

    assert environment["spring.cloud.aws.credentials.accessKey"] == s3_app_data["access-key"]
    assert environment["spring.cloud.aws.credentials.secretKey"] == s3_app_data["secret-key"]
    assert environment["spring.cloud.aws.region.static"] == s3_app_data["region"]
    assert environment["spring.cloud.aws.s3.bucket"] == s3_app_data["bucket"]
    assert environment["spring.cloud.aws.s3.endpoint"] == s3_app_data["endpoint"]


def test_mongodb_integration(
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
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    mongodb_relation = out.get_relations("mongodb")
    assert len(mongodb_relation) == 1

    assert (
        environment["spring.data.mongodb.uri"]
        == "mongodb://test-mongodb-username:test-mongodb-password@test-mongodb:27017/spring-boot-k8s"
    )


def test_mysql_integration(
    mysql_base_state,
) -> None:
    """
    arrange: add mysql relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: the springboot charm should have the mysql related env variables.
    """
    state = testing.State(**mysql_base_state)
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    mysql_relation = out.get_relations("mysql")
    assert len(mysql_relation) == 1

    assert environment["spring.datasource.username"] == "test-username"
    assert environment["spring.datasource.password"] == "test-password"
    assert environment["spring.datasource.url"] == "jdbc:mysql://test-mysql:3306/spring-boot-k8s"
    assert environment["spring.jpa.hibernate.ddl-auto"] == "none"
    assert environment["MYSQL_DB_NAME"] == "spring-boot-k8s"


def test_openfga_integration(
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
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert out.unit_status == testing.ActiveStatus()

    openfga_relation = out.get_relations("openfga")
    assert len(openfga_relation) == 1

    assert environment["openfga.store-id"] == "test-store-id"
    assert environment["openfga.credentials.method"] == "API_TOKEN"
    assert environment["openfga.credentials.config.api-token"] == "test-token"
    assert environment["openfga.api-url"] == "localhost:8080"


def test_rabbitmq_integration(
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
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
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


def test_oauth_integration(base_state: dict) -> None:
    """
    arrange: TODO
    act: TODO
    assert: TODO
    """

    secret_id = token_hex(16)
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=SpringBootCharm,
    )
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.ActiveStatus()

    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"] = [testing.Secret(id=secret_id, tracked_content={"secret": "abc"})]

    state = testing.State(**base_state)
    out = context.run(context.on.relation_changed(oauth_relation), state)
    environment = list(out.containers)[0].plan.services["spring-boot"].environment
    assert (
        environment["spring.security.oauth2.client.registration.hydra.client-id"]
        == "test-client-id"
    )
    assert environment["spring.security.oauth2.client.registration.hydra.client-secret"] == "abc"
    assert (
        environment["spring.security.oauth2.client.registration.hydra.scope"]
        == "openid,profile,email"
    )
    assert (
        environment["spring.security.oauth2.client.registration.hydra.authorization-grant-type"]
        == "authorization_code"
    )
    assert (
        environment["spring.security.oauth2.client.registration.hydra.redirect-uri"]
        == "http://juju.test//login/oauth2/code/oidc"
    )
    assert (
        environment["spring.security.oauth2.client.provider.hydra.authorization-uri"]
        == "https://traefik_ip/model_name-hydra/oauth2/auth"
    )
    assert (
        environment["spring.security.oauth2.client.provider.hydra.token-uri"]
        == "https://traefik_ip/model_name-hydra/oauth2/token"
    )
    assert (
        environment["spring.security.oauth2.client.registration.hydra.user-name-attribute"]
        == "sub"
    )
    assert environment["spring.security.oauth2.client.provider.hydra.user-name-attribute"] == "sub"
    assert (
        environment["spring.security.oauth2.client.provider.hydra.user-info-uri"]
        == "https://traefik_ip/model_name-hydra/userinfo"
    )
    assert (
        environment["spring.security.oauth2.client.provider.hydra.jwk-set-uri"]
        == "https://traefik_ip/model_name-hydra/.well-known/jwks.json"
    )
    assert (
        environment["spring.security.oauth2.client.provider.hydra.issuer-uri"]
        == "https://traefik_ip/model_name-hydra"
    )
    assert environment["server.forward-headers-strategy"] == "framework"
