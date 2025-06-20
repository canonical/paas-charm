# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Springboot charm unit tests for integrations."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

from ops import testing

from examples.springboot.charm.src.charm import SpringBootCharm


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
