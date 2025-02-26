# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integrations unit tests."""
import itertools
import json

import pytest
from ops.testing import Harness

from paas_charm.app import map_integrations_to_env
from paas_charm.charm_state import (
    IntegrationsState,
    S3Parameters,
    SamlParameters,
    SmtpParameters,
    TempoParameters,
    generate_relation_parameters,
)
from tests.unit.flask.constants import (
    INTEGRATIONS_RELATION_DATA,
    SAML_APP_RELATION_DATA_EXAMPLE,
    SMTP_RELATION_DATA_EXAMPLE,
)


def _generate_map_integrations_to_env_parameters(prefix: str = ""):
    empty_env = pytest.param(
        IntegrationsState(),
        prefix,
        {},
        id="no new env vars",
    )
    redis_env = pytest.param(
        IntegrationsState(redis_uri="http://redisuri"),
        prefix,
        {
            f"{prefix}REDIS_DB_CONNECT_STRING": "http://redisuri",
            f"{prefix}REDIS_DB_FRAGMENT": "",
            f"{prefix}REDIS_DB_HOSTNAME": "redisuri",
            f"{prefix}REDIS_DB_NETLOC": "redisuri",
            f"{prefix}REDIS_DB_PARAMS": "",
            f"{prefix}REDIS_DB_PATH": "",
            f"{prefix}REDIS_DB_QUERY": "",
            f"{prefix}REDIS_DB_SCHEME": "http",
        },
        id=f"With Redis uri, prefix: {prefix}",
    )
    saml_env = pytest.param(
        IntegrationsState(
            saml_parameters=generate_relation_parameters(
                SAML_APP_RELATION_DATA_EXAMPLE, SamlParameters, True
            )
        ),
        prefix,
        {
            f"{prefix}SAML_ENTITY_ID": "https://login.staging.ubuntu.com",
            f"{prefix}SAML_METADATA_URL": "https://login.staging.ubuntu.com/saml/metadata",
            f"{prefix}SAML_SIGNING_CERTIFICATE": "MIIDuzCCAqOgAwIBAgIJALRwYFkmH3k9MA0GCSqGSIb3DQEBCwUAMHQxCzAJBgNVBAYTAkdCMRMwEQYDVQQIDApTb21lLVN0YXRlMSswKQYDVQQKDCJTU08gU3RhZ2luZyBrZXkgZm9yIEV4cGVuc2lmeSBTQU1MMSMwIQYDVQQDDBpTU08gU3RhZ2luZyBFeHBlbnNpZnkgU0FNTDAeFw0xNTA5MjUxMDUzNTZaFw0xNjA5MjQxMDUzNTZaMHQxCzAJBgNVBAYTAkdCMRMwEQYDVQQIDApTb21lLVN0YXRlMSswKQYDVQQKDCJTU08gU3RhZ2luZyBrZXkgZm9yIEV4cGVuc2lmeSBTQU1MMSMwIQYDVQQDDBpTU08gU3RhZ2luZyBFeHBlbnNpZnkgU0FNTDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANyt2LqrD3DSmJMtNUA5xjJpbUNuiaHFdO0AduOegfM7YnKIp0Y001S07ffEcv/zNo7Gg6wAZwLtW2/+eUkRj8PLEyYDyU2NiwD7stAzhz50AjTbLojRyZdrEo6xu+f43xFNqf78Ix8mEKFr0ZRVVkkNRifa4niXPDdzIUiv5UZUGjW0ybFKdM3zm6xjEwMwo8ixu/IbAn74PqC7nypllCvLjKLFeYmYN24oYaVKWIRhQuGL3m98eQWFiVUL40palHtgcy5tffg8UOyAOqg5OF2kGVeyPZNmjq/jVHYyBUtBaMvrTLUlOKRRC3I+aW9tXs7aqclQytOiFQxq+aEapB8CAwEAAaNQME4wHQYDVR0OBBYEFA9Ub7RIfw21Qgbnf4IA3n4jUpAlMB8GA1UdIwQYMBaAFA9Ub7RIfw21Qgbnf4IA3n4jUpAlMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBAGBHECvs8V3xBKGRvNfBaTbY2FpbwLheSm3MUM4/hswvje24oknoHMF3dFNVnosOLXYdaRf8s0rsJfYuoUTap9tKzv0osGoA3mMw18LYW3a+mUHurx+kJZP+VN3emk84TXiX44CCendMVMxHxDQwg40YxALNc4uew2hlLReB8nC+55OlsIInIqPcIvtqUZgeNp2iecKnCgZPDaElez52GY5GRFszJd04sAQIrpg2+xfZvLMtvWwb9rpdto5oIdat2gIoMLdrmJUAYWP2+BLiKVpe9RtzfvqtQrk1lDoTj3adJYutNIPbTGOfI/Vux0HCw9KCrNTspdsfGTIQFJJi01E=",
            f"{prefix}SAML_SINGLE_SIGN_ON_REDIRECT_URL": "https://login.staging.ubuntu.com/saml/",
        },
        id=f"With Saml, prefix: {prefix}",
    )
    tempo_env = pytest.param(
        IntegrationsState(
            tempo_parameters=generate_relation_parameters(
                {
                    "service_name": "test_app",
                    "endpoint": "http://test-ip:4318",
                },
                TempoParameters,
            )
        ),
        prefix,
        {
            f"{prefix}OTEL_EXPORTER_OTLP_ENDPOINT": "http://test-ip:4318",
            f"{prefix}OTEL_SERVICE_NAME": "test_app",
        },
        id=f"With Tempo, prefix: {prefix}",
    )
    rabbitmq_env = pytest.param(
        IntegrationsState(
            rabbitmq_uri="amqp://test-app:3m036hhyiDHs@rabbitmq-k8s-endpoints.testing.svc.cluster.local:5672/"
        ),
        prefix,
        {
            f"{prefix}RABBITMQ_CONNECT_STRING": "amqp://test-app:3m036hhyiDHs@rabbitmq-k8s-endpoints.testing.svc.cluster.local:5672/",
            f"{prefix}RABBITMQ_FRAGMENT": "",
            f"{prefix}RABBITMQ_HOSTNAME": "rabbitmq-k8s-endpoints.testing.svc.cluster.local",
            f"{prefix}RABBITMQ_NETLOC": "test-app:3m036hhyiDHs@rabbitmq-k8s-endpoints.testing.svc.cluster.local:5672",
            f"{prefix}RABBITMQ_PARAMS": "",
            f"{prefix}RABBITMQ_PASSWORD": "3m036hhyiDHs",
            f"{prefix}RABBITMQ_PATH": "/",
            f"{prefix}RABBITMQ_PORT": "5672",
            f"{prefix}RABBITMQ_QUERY": "",
            f"{prefix}RABBITMQ_SCHEME": "amqp",
            f"{prefix}RABBITMQ_USERNAME": "test-app",
        },
        id=f"With RabbitMQ, prefix: {prefix}",
    )
    smtp_env = pytest.param(
        IntegrationsState(
            smtp_parameters=generate_relation_parameters(
                SMTP_RELATION_DATA_EXAMPLE, SmtpParameters
            )
        ),
        prefix,
        {
            f"{prefix}SMTP_DOMAIN": "example.com",
            f"{prefix}SMTP_HOST": "test-ip",
            f"{prefix}SMTP_PORT": "1025",
            f"{prefix}SMTP_SKIP_SSL_VERIFY": "False",
        },
        id=f"With SMTP, prefix: {prefix}",
    )
    databases_env = pytest.param(
        IntegrationsState(
            databases_uris={
                "postgresql": "postgresql://test-username:test-password@test-postgresql:5432/test-database?connect_timeout=10",
                "mysql": "mysql://test-username:test-password@test-mysql:3306/test-app",
                "mongodb": None,
                "futuredb": "futuredb://foobar/",
            },
        ),
        prefix,
        {
            f"{prefix}POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/test-database?connect_timeout=10",
            f"{prefix}POSTGRESQL_DB_FRAGMENT": "",
            f"{prefix}POSTGRESQL_DB_HOSTNAME": "test-postgresql",
            f"{prefix}POSTGRESQL_DB_NAME": "test-database",
            f"{prefix}POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
            f"{prefix}POSTGRESQL_DB_PARAMS": "",
            f"{prefix}POSTGRESQL_DB_PASSWORD": "test-password",
            f"{prefix}POSTGRESQL_DB_PATH": "/test-database",
            f"{prefix}POSTGRESQL_DB_PORT": "5432",
            f"{prefix}POSTGRESQL_DB_QUERY": "connect_timeout=10",
            f"{prefix}POSTGRESQL_DB_SCHEME": "postgresql",
            f"{prefix}POSTGRESQL_DB_USERNAME": "test-username",
            f"{prefix}MYSQL_DB_CONNECT_STRING": "mysql://test-username:test-password@test-mysql:3306/test-app",
            f"{prefix}MYSQL_DB_FRAGMENT": "",
            f"{prefix}MYSQL_DB_HOSTNAME": "test-mysql",
            f"{prefix}MYSQL_DB_NAME": "test-app",
            f"{prefix}MYSQL_DB_NETLOC": "test-username:test-password@test-mysql:3306",
            f"{prefix}MYSQL_DB_PARAMS": "",
            f"{prefix}MYSQL_DB_PASSWORD": "test-password",
            f"{prefix}MYSQL_DB_PATH": "/test-app",
            f"{prefix}MYSQL_DB_PORT": "3306",
            f"{prefix}MYSQL_DB_QUERY": "",
            f"{prefix}MYSQL_DB_SCHEME": "mysql",
            f"{prefix}MYSQL_DB_USERNAME": "test-username",
            f"{prefix}FUTUREDB_DB_CONNECT_STRING": "futuredb://foobar/",
            f"{prefix}FUTUREDB_DB_FRAGMENT": "",
            f"{prefix}FUTUREDB_DB_HOSTNAME": "foobar",
            f"{prefix}FUTUREDB_DB_NAME": "",
            f"{prefix}FUTUREDB_DB_NETLOC": "foobar",
            f"{prefix}FUTUREDB_DB_PARAMS": "",
            f"{prefix}FUTUREDB_DB_PATH": "/",
            f"{prefix}FUTUREDB_DB_QUERY": "",
            f"{prefix}FUTUREDB_DB_SCHEME": "futuredb",
        },
        id=f"With several databases, one of them None. prefix: {prefix}",
    )
    small_s3 = pytest.param(
        IntegrationsState(
            s3_parameters=S3Parameters.model_construct(
                access_key="access_key",
                secret_key="secret_key",
                bucket="bucket",
            ),
        ),
        prefix,
        {
            f"{prefix}S3_ACCESS_KEY": "access_key",
            f"{prefix}S3_SECRET_KEY": "secret_key",
            f"{prefix}S3_BUCKET": "bucket",
        },
        id=f"With minimal variables in S3 Integration. prefix: {prefix}",
    )
    full_s3 = pytest.param(
        IntegrationsState(
            s3_parameters=S3Parameters.model_construct(
                access_key="access_key",
                secret_key="secret_key",
                region="region",
                storage_class="GLACIER",
                bucket="bucket",
                endpoint="https://s3.example.com",
                path="/path/subpath/",
                s3_api_version="s3v4",
                uri_style="host",
                tls_ca_chain=(
                    ca_chain := [
                        "-----BEGIN CERTIFICATE-----\nTHE FIRST LONG CERTIFICATE\n-----END CERTIFICATE-----",
                        "-----BEGIN CERTIFICATE-----\nTHE SECOND LONG CERTIFICATE\n-----END CERTIFICATE-----",
                    ]
                ),
                attributes=(
                    attributes := [
                        "header1:value1",
                        "header2:value2",
                    ]
                ),
            ),
        ),
        prefix,
        {
            f"{prefix}S3_ACCESS_KEY": "access_key",
            f"{prefix}S3_SECRET_KEY": "secret_key",
            f"{prefix}S3_API_VERSION": "s3v4",
            f"{prefix}S3_BUCKET": "bucket",
            f"{prefix}S3_ENDPOINT": "https://s3.example.com",
            f"{prefix}S3_PATH": "/path/subpath/",
            f"{prefix}S3_REGION": "region",
            f"{prefix}S3_STORAGE_CLASS": "GLACIER",
            f"{prefix}S3_ATTRIBUTES": json.dumps(attributes),
            f"{prefix}S3_TLS_CA_CHAIN": json.dumps(ca_chain),
        },
        id=f"With all variables in S3 Integration. prefix: {prefix}",
    )
    return [
        empty_env,
        redis_env,
        saml_env,
        tempo_env,
        rabbitmq_env,
        smtp_env,
        databases_env,
        small_s3,
        full_s3,
    ]


def _test_map_integrations_to_env_parameters():

    prefixes = ["FLASK_", "DJANGO_", ""]
    return itertools.chain.from_iterable(
        _generate_map_integrations_to_env_parameters(prefix) for prefix in prefixes
    )


@pytest.mark.parametrize(
    "integrations, prefix, expected_env", _test_map_integrations_to_env_parameters()
)
def test_map_integrations_to_env(
    integrations,
    prefix,
    expected_env,
):
    """
    arrange: prepare integrations state.
    act: call to generate mappings to env variables.
    assert: the variables generated should be the expected ones.
    """
    env = map_integrations_to_env(integrations, prefix)
    assert env == expected_env
