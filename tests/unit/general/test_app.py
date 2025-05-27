# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""App unit tests."""

import pytest
from charms.saml_integrator.v0.saml import SamlEndpoint

from paas_charm.app import (
    generate_rabbitmq_env,
    generate_redis_env,
    generate_s3_env,
    generate_saml_env,
    generate_tempo_env,
)
from paas_charm.rabbitmq import RabbitMQRelationData
from paas_charm.redis import PaaSRedisRelationData
from paas_charm.s3 import S3RelationData
from paas_charm.saml import PaaSSAMLRelationData
from paas_charm.tempo import TempoRelationData


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            RabbitMQRelationData.model_construct(
                port=5672,
                hostname="test-url.com",
                username="testusername",
                password="testpassword",
                amqp_uri="amqp://testusername:testpassword@test-url.com:5672",
                vhost="",
            ),
            {
                "RABBITMQ_CONNECT_STRING": "amqp://testusername:testpassword@test-url.com:5672/",
                "RABBITMQ_FRAGMENT": "",
                "RABBITMQ_HOSTNAME": "test-url.com",
                "RABBITMQ_NETLOC": "testusername:testpassword@test-url.com:5672",
                "RABBITMQ_PARAMS": "",
                "RABBITMQ_PASSWORD": "testpassword",
                "RABBITMQ_PATH": "/",
                "RABBITMQ_PORT": "5672",
                "RABBITMQ_QUERY": "",
                "RABBITMQ_SCHEME": "amqp",
                "RABBITMQ_USERNAME": "testusername",
            },
            id="All relation data",
        ),
    ],
)
def test_rabbitmq_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given S3 relation data.
    act: when generate_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_rabbitmq_env(relation_data) == expected_env


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            PaaSRedisRelationData.model_construct(url="redis://localhost"),
            {
                "REDIS_DB_CONNECT_STRING": "redis://localhost",
                "REDIS_DB_FRAGMENT": "",
                "REDIS_DB_HOSTNAME": "localhost",
                "REDIS_DB_NETLOC": "localhost",
                "REDIS_DB_PARAMS": "",
                "REDIS_DB_PATH": "",
                "REDIS_DB_QUERY": "",
                "REDIS_DB_SCHEME": "redis",
            },
            id="Minimum redis DSN",
        ),
        pytest.param(
            PaaSRedisRelationData.model_construct(url="redis://secret@localhost/1"),
            {
                "REDIS_DB_CONNECT_STRING": "redis://secret@localhost/1",
                "REDIS_DB_FRAGMENT": "",
                "REDIS_DB_HOSTNAME": "localhost",
                "REDIS_DB_NAME": "1",
                "REDIS_DB_NETLOC": "secret@localhost",
                "REDIS_DB_PARAMS": "",
                "REDIS_DB_PATH": "/1",
                "REDIS_DB_QUERY": "",
                "REDIS_DB_SCHEME": "redis",
                "REDIS_DB_USERNAME": "secret",
            },
            id="Max redis DSN",
        ),
        pytest.param(
            PaaSRedisRelationData.model_construct(url="http://redisuri"),
            {
                "REDIS_DB_CONNECT_STRING": "http://redisuri",
                "REDIS_DB_FRAGMENT": "",
                "REDIS_DB_HOSTNAME": "redisuri",
                "REDIS_DB_NETLOC": "redisuri",
                "REDIS_DB_PARAMS": "",
                "REDIS_DB_PATH": "",
                "REDIS_DB_QUERY": "",
                "REDIS_DB_SCHEME": "http",
            },
            id="http redis DSN",
        ),
    ],
)
def test_redis_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given Redis relation data.
    act: when generate_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_redis_env(relation_data) == expected_env


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            S3RelationData.model_construct(
                access_key="access_key", secret_key="secret_key", bucket="bucket"
            ),
            {
                "S3_ACCESS_KEY": "access_key",
                "S3_SECRET_KEY": "secret_key",
                "S3_BUCKET": "bucket",
            },
            id="Minimum relation data",
        ),
        pytest.param(
            S3RelationData.model_construct(
                access_key="access_key",
                secret_key="secret_key",
                region="region",
                storage_class="standard",
                bucket="bucket",
                endpoint="endpoint",
                path="path",
                s3_api_version="version",
                s3_uri_style="url-style",
                tls_ca_chain=["---first---", "---second---"],
                attributes=["key1", "key2"],
            ),
            {
                "S3_ACCESS_KEY": "access_key",
                "S3_ADDRESSING_STYLE": "url-style",
                "S3_API_VERSION": "version",
                "S3_ATTRIBUTES": '["key1", "key2"]',
                "S3_BUCKET": "bucket",
                "S3_ENDPOINT": "endpoint",
                "S3_PATH": "path",
                "S3_REGION": "region",
                "S3_SECRET_KEY": "secret_key",
                "S3_STORAGE_CLASS": "standard",
                "S3_URI_STYLE": "url-style",
                "S3_TLS_CA_CHAIN": '["---first---", "---second---"]',
            },
            id="All relation data",
        ),
    ],
)
def test_s3_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given S3 relation data.
    act: when generate_s3_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_s3_env(relation_data) == expected_env


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            PaaSSAMLRelationData.model_construct(
                entity_id="test-entity-id",
                metadata_url=None,
                certificates=("test-certificate-1",),
                endpoints=(
                    SamlEndpoint(
                        name="test-endpoint",
                        url="http://testing-endpoint.test",
                        binding="test-binding",
                        response_url="http://response-url.test",
                    ),
                ),
            ),
            {
                "SAML_ENTITY_ID": "test-entity-id",
                "SAML_SIGNING_CERTIFICATE": "test-certificate-1",
            },
            id="Minimum relation data",
        ),
        pytest.param(
            PaaSSAMLRelationData.model_construct(
                entity_id="https://login.staging.ubuntu.com",
                metadata_url="https://login.staging.ubuntu.com/saml/metadata",
                certificates=("https://login.staging.ubuntu.com/saml/", "test-certificate-2"),
                endpoints=(
                    SamlEndpoint(
                        name="SingleSignOnService",
                        url="http://testing-redirect-url.test",
                        binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                        response_url="http://response-url.test",
                    ),
                    SamlEndpoint(
                        name="other_endpoint",
                        url="http://other-url.test",
                        binding="test-binding",
                        response_url="http://response-url.test",
                    ),
                ),
            ),
            {
                "SAML_ENTITY_ID": "https://login.staging.ubuntu.com",
                "SAML_METADATA_URL": "https://login.staging.ubuntu.com/saml/metadata",
                "SAML_SINGLE_SIGN_ON_REDIRECT_URL": "http://testing-redirect-url.test/",
                "SAML_SIGNING_CERTIFICATE": "https://login.staging.ubuntu.com/saml/",
            },
            id="All relation data",
        ),
    ],
)
def test_saml_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given SAML relation data.
    act: when generate_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_saml_env(relation_data) == expected_env


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            TempoRelationData.model_construct(
                endpoint="http://tempo-endpoint.test",
                service_name="app-name",
            ),
            {
                "OTEL_SERVICE_NAME": "app-name",
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://tempo-endpoint.test",
            },
            id="Relation data",
        ),
    ],
)
def test_tempo_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given Tempo relation data.
    act: when generate_tempo_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_tempo_env(relation_data) == expected_env
