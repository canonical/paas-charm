# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integrations unit tests."""
import json
import pathlib
import unittest
from types import NoneType
from unittest.mock import MagicMock

import pytest
from charms.openfga_k8s.v1.openfga import OpenfgaProviderAppData, OpenFGARequires
from charms.saml_integrator.v0.saml import SamlEndpoint
from charms.smtp_integrator.v0.smtp import (
    AuthType,
    SmtpRelationData,
    SmtpRequires,
    TransportSecurity,
)
from ops import ActiveStatus, RelationMeta, RelationRole

import paas_charm
from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm._gunicorn.wsgi_app import WsgiApp
from paas_charm.app import App
from paas_charm.charm_state import CharmState, IntegrationsState
from paas_charm.databases import PaaSDatabaseRelationData
from paas_charm.rabbitmq import PaaSRabbitMQRelationData
from paas_charm.redis import PaaSRedisRelationData
from paas_charm.s3 import PaaSS3RelationData
from paas_charm.saml import PaaSSAMLRelationData
from paas_charm.tracing import PaaSTracingRelationData
from tests.unit.django.constants import DJANGO_CONTAINER_NAME
from tests.unit.expressjs.constants import EXPRESSJS_CONTAINER_NAME
from tests.unit.fastapi.constants import FASTAPI_CONTAINER_NAME
from tests.unit.flask.constants import (
    FLASK_CONTAINER_NAME,
    INTEGRATIONS_RELATION_DATA,
    OPENFGA_RELATION_DATA_EXAMPLE,
    SMTP_RELATION_DATA_EXAMPLE,
)
from tests.unit.go.constants import GO_CONTAINER_NAME


def _generate_map_integrations_to_env_parameters(prefix: str = ""):
    empty_env = pytest.param(
        IntegrationsState(),
        prefix,
        {},
        id="no new env vars",
    )
    return [empty_env]


def _test_integrations_state_build_parameters():
    relation_dict: dict[str, str] = {
        "redis": None,
        "database": {},
        "s3": None,
        "saml_relation_data": None,
        "rabbitmq": None,
        "tempo_relation_data": None,
        "smtp_relation_data": None,
        "openfga_relation_data": None,
    }

    return [
        pytest.param(
            {**relation_dict, "s3": INTEGRATIONS_RELATION_DATA["s3"]["app_data"]},
            False,
            id="S3 correct parameters",
        ),
        pytest.param(
            {**relation_dict, "smtp_relation_data": SMTP_RELATION_DATA_EXAMPLE},
            False,
            id="Smtp correct parameters",
        ),
        pytest.param(
            {**relation_dict, "smtp_relation_data": {}},
            False,
            id="Smtp empty parameters",
        ),
        pytest.param(
            {
                **relation_dict,
                "rabbitmq_uri": "amqp://test-app:3m036hhyiDHs@rabbitmq-k8s-endpoints.testing.svc.cluster.local:5672/",
            },
            False,
            id="RabbitMQ correct parameters",
        ),
        pytest.param(
            {**relation_dict, "rabbitmq_uri": "http://redisuri"},
            False,
            id="RabbitMQ empty parameters",
        ),
        pytest.param(
            {**relation_dict, "openfga_relation_data": OPENFGA_RELATION_DATA_EXAMPLE},
            False,
            id="OpenFGA correct parameters",
        ),
        pytest.param(
            {**relation_dict, "openfga_relation_data": {}},
            False,
            id="OpenFGA empty parameters",
        ),
    ]


def _test_integrations_env_parameters():

    parameters_with_empty_prefix = _generate_map_integrations_to_env_parameters()

    return [pytest.param(p.values[0], p.values[2], id=p.id) for p in parameters_with_empty_prefix]


@pytest.mark.parametrize(
    "integrations, expected_env",
    [
        pytest.param(
            IntegrationsState(
                databases_relation_data={
                    "postgresql": PaaSDatabaseRelationData(
                        uris="postgresql://testingusername:testingpassword@netlocation.test:5432/"
                        "testingdbname?parameter=testparam"
                    )
                }
            ),
            {
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://testingusername:testingpassword@netlocation.test:5432/testingdbname?parameter=testparam",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "netlocation.test",
                "POSTGRESQL_DB_NAME": "testingdbname",
                "POSTGRESQL_DB_NETLOC": "testingusername:testingpassword@netlocation.test:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "testingpassword",
                "POSTGRESQL_DB_PATH": "/testingdbname",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "parameter=testparam",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "testingusername",
            },
            id="Postgres (Full DSN)",
        ),
        pytest.param(
            IntegrationsState(
                databases_relation_data={
                    "postgresql": PaaSDatabaseRelationData(uris="postgresql://netlocation.test")
                }
            ),
            {
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://netlocation.test",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "netlocation.test",
                "POSTGRESQL_DB_NETLOC": "netlocation.test",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PATH": "",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
            },
            id="Postgres (Minimum DSN)",
        ),
        pytest.param(
            IntegrationsState(
                databases_relation_data={
                    "msyql": PaaSDatabaseRelationData(
                        uris="mysql://testingusername:testingpassword@localhost:3306/testingdbname"
                    )
                }
            ),
            {
                "MSYQL_DB_CONNECT_STRING": "mysql://testingusername:testingpassword@localhost:3306/testingdbname",
                "MSYQL_DB_FRAGMENT": "",
                "MSYQL_DB_HOSTNAME": "localhost",
                "MSYQL_DB_NAME": "testingdbname",
                "MSYQL_DB_NETLOC": "testingusername:testingpassword@localhost:3306",
                "MSYQL_DB_PARAMS": "",
                "MSYQL_DB_PASSWORD": "testingpassword",
                "MSYQL_DB_PATH": "/testingdbname",
                "MSYQL_DB_PORT": "3306",
                "MSYQL_DB_QUERY": "",
                "MSYQL_DB_SCHEME": "mysql",
                "MSYQL_DB_USERNAME": "testingusername",
            },
            id="MySQL",
        ),
        pytest.param(
            IntegrationsState(
                databases_relation_data={
                    "mongodb": PaaSDatabaseRelationData(
                        uris="mongodb+srv://testinguser:testingpassword@cluster0.example.mongodb.net/?retryWrites=true&w=majority"
                    )
                }
            ),
            {
                "MONGODB_DB_CONNECT_STRING": "mongodb+srv://testinguser:testingpassword@cluster0.example.mongodb.net/?retryWrites=true&w=majority",
                "MONGODB_DB_FRAGMENT": "",
                "MONGODB_DB_HOSTNAME": "cluster0.example.mongodb.net",
                "MONGODB_DB_NAME": "",
                "MONGODB_DB_NETLOC": "testinguser:testingpassword@cluster0.example.mongodb.net",
                "MONGODB_DB_PARAMS": "",
                "MONGODB_DB_PASSWORD": "testingpassword",
                "MONGODB_DB_PATH": "/",
                "MONGODB_DB_QUERY": "retryWrites=true&w=majority",
                "MONGODB_DB_SCHEME": "mongodb+srv",
                "MONGODB_DB_USERNAME": "testinguser",
            },
            id="MongoDB",
        ),
        pytest.param(
            IntegrationsState(
                openfga=OpenfgaProviderAppData(
                    store_id="test-store-id",
                    token="test-token",
                    grpc_api_url="localhost:8081",
                    http_api_url="localhost:8080",
                )
            ),
            {
                "FGA_GRPC_API_URL": "localhost:8081",
                "FGA_HTTP_API_URL": "localhost:8080",
                "FGA_STORE_ID": "test-store-id",
                "FGA_TOKEN": "test-token",
            },
            id="OpenFGA",
        ),
        pytest.param(
            IntegrationsState(
                rabbitmq=PaaSRabbitMQRelationData(
                    vhost="/",
                    port=5672,
                    hostname="testinghostname",
                    username="testingusername",
                    password="testingpassword",
                )
            ),
            {
                "RABBITMQ_CONNECT_STRING": "amqp://testingusername:testingpassword@testinghostname:5672/%2F",
                "RABBITMQ_FRAGMENT": "",
                "RABBITMQ_HOSTNAME": "testinghostname",
                "RABBITMQ_NETLOC": "testingusername:testingpassword@testinghostname:5672",
                "RABBITMQ_PARAMS": "",
                "RABBITMQ_PASSWORD": "testingpassword",
                "RABBITMQ_PATH": "/%2F",
                "RABBITMQ_PORT": "5672",
                "RABBITMQ_QUERY": "",
                "RABBITMQ_SCHEME": "amqp",
                "RABBITMQ_USERNAME": "testingusername",
                "RABBITMQ_VHOST": "/",
            },
            id="RabbitMQ",
        ),
        pytest.param(
            IntegrationsState(
                redis=PaaSRedisRelationData(
                    url="redis://testingusername:testingpassword@localhost:6379?db=0&timeout=5"
                ),
            ),
            {
                "REDIS_DB_CONNECT_STRING": "redis://testingusername:testingpassword@localhost:6379?db=0&timeout=5",
                "REDIS_DB_FRAGMENT": "",
                "REDIS_DB_HOSTNAME": "localhost",
                "REDIS_DB_NETLOC": "testingusername:testingpassword@localhost:6379",
                "REDIS_DB_PARAMS": "",
                "REDIS_DB_PASSWORD": "testingpassword",
                "REDIS_DB_PATH": "",
                "REDIS_DB_PORT": "6379",
                "REDIS_DB_QUERY": "db=0&timeout=5",
                "REDIS_DB_SCHEME": "redis",
                "REDIS_DB_USERNAME": "testingusername",
            },
            id="Redis",
        ),
        pytest.param(
            IntegrationsState(
                s3=PaaSS3RelationData.model_construct(
                    access_key="TESTINGACCESSKEY",
                    secret_key="TESTINGSECRETKEY",
                    region="us-west-1",
                    storage_class="STANDARD",
                    bucket="my-example-bucket",
                    endpoint="https://s3.storagebucket.internal",
                    path="uploads/",
                    s3_api_version="2006-03-01",
                    s3_uri_style="path",
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
                )
            ),
            {
                "S3_ACCESS_KEY": "TESTINGACCESSKEY",
                "S3_ADDRESSING_STYLE": "path",
                "S3_API_VERSION": "2006-03-01",
                "S3_BUCKET": "my-example-bucket",
                "S3_ENDPOINT": "https://s3.storagebucket.internal",
                "S3_PATH": "uploads/",
                "S3_REGION": "us-west-1",
                "S3_SECRET_KEY": "TESTINGSECRETKEY",
                "S3_STORAGE_CLASS": "STANDARD",
                "S3_URI_STYLE": "path",
                "S3_ATTRIBUTES": json.dumps(attributes),
                "S3_TLS_CA_CHAIN": json.dumps(ca_chain),
            },
            id="S3",
        ),
        pytest.param(
            IntegrationsState(
                saml=PaaSSAMLRelationData(
                    entity_id="testing-entity-id",
                    metadata_url="https://saml.example.com/metadata.xml",
                    certificates=(
                        "MIIDuzCCAqOgAwIBAgIJALRwYFkmH3k9MA0GCSqGSIb3DQEBCwUAMHQxCzAJBgNVBAYTAkdCMRMwEQYDVQQIDApTb21lLVN0YXRlMSswKQYDVQQKDCJTU08gU3RhZ2luZyBrZXkgZm9yIEV4cGVuc2lmeSBTQU1MMSMwIQYDVQQDDBpTU08gU3RhZ2luZyBFeHBlbnNpZnkgU0FNTDAeFw0xNTA5MjUxMDUzNTZaFw0xNjA5MjQxMDUzNTZaMHQxCzAJBgNVBAYTAkdCMRMwEQYDVQQIDApTb21lLVN0YXRlMSswKQYDVQQKDCJTU08gU3RhZ2luZyBrZXkgZm9yIEV4cGVuc2lmeSBTQU1MMSMwIQYDVQQDDBpTU08gU3RhZ2luZyBFeHBlbnNpZnkgU0FNTDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANyt2LqrD3DSmJMtNUA5xjJpbUNuiaHFdO0AduOegfM7YnKIp0Y001S07ffEcv/zNo7Gg6wAZwLtW2/+eUkRj8PLEyYDyU2NiwD7stAzhz50AjTbLojRyZdrEo6xu+f43xFNqf78Ix8mEKFr0ZRVVkkNRifa4niXPDdzIUiv5UZUGjW0ybFKdM3zm6xjEwMwo8ixu/IbAn74PqC7nypllCvLjKLFeYmYN24oYaVKWIRhQuGL3m98eQWFiVUL40palHtgcy5tffg8UOyAOqg5OF2kGVeyPZNmjq/jVHYyBUtBaMvrTLUlOKRRC3I+aW9tXs7aqclQytOiFQxq+aEapB8CAwEAAaNQME4wHQYDVR0OBBYEFA9Ub7RIfw21Qgbnf4IA3n4jUpAlMB8GA1UdIwQYMBaAFA9Ub7RIfw21Qgbnf4IA3n4jUpAlMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBAGBHECvs8V3xBKGRvNfBaTbY2FpbwLheSm3MUM4/hswvje24oknoHMF3dFNVnosOLXYdaRf8s0rsJfYuoUTap9tKzv0osGoA3mMw18LYW3a+mUHurx+kJZP+VN3emk84TXiX44CCendMVMxHxDQwg40YxALNc4uew2hlLReB8nC+55OlsIInIqPcIvtqUZgeNp2iecKnCgZPDaElez52GY5GRFszJd04sAQIrpg2+xfZvLMtvWwb9rpdto5oIdat2gIoMLdrmJUAYWP2+BLiKVpe9RtzfvqtQrk1lDoTj3adJYutNIPbTGOfI/Vux0HCw9KCrNTspdsfGTIQFJJi01E=",
                        "MIIDuzCCAqOgAwIBAgIJALRwYFkmH3k9MA0GCSqGSIb3DQEBCwUAMHQxCzAJBgNVBAYTAkdCMRMwEQYDVQQIDApTb21lLVN0YXRlMSswKQYDVQQKDCJTU08gU3RhZ2luZyBrZXkgZm9yIEV4cGVuc2lmeSBTQU1MMSMwIQYDVQQDDBpTU08gU3RhZ2luZyBFeHBlbnNpZnkgU0FNTDAeFw0xNTA5MjUxMDUzNTZaFw0xNjA5MjQxMDUzNTZaMHQxCzAJBgNVBAYTAkdCMRMwEQYDVQQIDApTb21lLVN0YXRlMSswKQYDVQQKDCJTU08gU3RhZ2luZyBrZXkgZm9yIEV4cGVuc2lmeSBTQU1MMSMwIQYDVQQDDBpTU08gU3RhZ2luZyBFeHBlbnNpZnkgU0FNTDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANyt2LqrD3DSmJMtNUA5xjJpbUNuiaHFdO0AduOegfM7YnKIp0Y001S07ffEcv/zNo7Gg6wAZwLtW2/+eUkRj8PLEyYDyU2NiwD7stAzhz50AjTbLojRyZdrEo6xu+f43xFNqf78Ix8mEKFr0ZRVVkkNRifa4niXPDdzIUiv5UZUGjW0ybFKdM3zm6xjEwMwo8ixu/IbAn74PqC7nypllCvLjKLFeYmYN24oYaVKWIRhQuGL3m98eQWFiVUL40palHtgcy5tffg8UOyAOqg5OF2kGVeyPZNmjq/jVHYyBUtBaMvrTLUlOKRRC3I+aW9tXs7aqclQytOiFQxq+aEapB8CAwEAAaNQME4wHQYDVR0OBBYEFA9Ub7RIfw21Qgbnf4IA3n4jUpAlMB8GA1UdIwQYMBaAFA9Ub7RIfw21Qgbnf4IA3n4jUpAlMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBAGBHECvs8V3xBKGRvNfBaTbY2FpbwLheSm3MUM4/hswvje24oknoHMF3dFNVnosOLXYdaRf8s0rsJfYuoUTap9tKzv0osGoA3mMw18LYW3a+mUHurx+kJZP+VN3emk84TXiX44CCendMVMxHxDQwg40YxALNc4uew2hlLReB8nC+55OlsIInIqPcIvtqUZgeNp2iecKnCgZPDaElez52GY5GRFszJd04sAQIrpg2+xfZvLMtvWwb9rpdto5oIdat2gIoMLdrmJUAYWP2+BLiKVpe9RtzfvqtQrk1lDoTj3adJYutNIPbTGOfI/Vux0HCw9KCrNTspdsfGTIQFJJi01E=",
                    ),
                    endpoints=(
                        SamlEndpoint(
                            name="SingleSignOnService",
                            url="http://test-single-signon-url.test",
                            binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                            response_url="http://test-response-url.test",
                        ),
                        SamlEndpoint(
                            name="SingleSignOnService",
                            url="http://test-single-signon-url.test",
                            binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Post",
                            response_url="http://test-response-url.test",
                        ),
                    ),
                )
            ),
            {
                "SAML_ENTITY_ID": "testing-entity-id",
                "SAML_METADATA_URL": "https://saml.example.com/metadata.xml",
                "SAML_SIGNING_CERTIFICATE": "MIIDuzCCAqOgAwIBAgIJALRwYFkmH3k9MA0GCSqGSIb3DQEBCwUAMHQxCzAJBgNVBAYTAkdCMRMwEQYDVQQIDApTb21lLVN0YXRlMSswKQYDVQQKDCJTU08gU3RhZ2luZyBrZXkgZm9yIEV4cGVuc2lmeSBTQU1MMSMwIQYDVQQDDBpTU08gU3RhZ2luZyBFeHBlbnNpZnkgU0FNTDAeFw0xNTA5MjUxMDUzNTZaFw0xNjA5MjQxMDUzNTZaMHQxCzAJBgNVBAYTAkdCMRMwEQYDVQQIDApTb21lLVN0YXRlMSswKQYDVQQKDCJTU08gU3RhZ2luZyBrZXkgZm9yIEV4cGVuc2lmeSBTQU1MMSMwIQYDVQQDDBpTU08gU3RhZ2luZyBFeHBlbnNpZnkgU0FNTDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBANyt2LqrD3DSmJMtNUA5xjJpbUNuiaHFdO0AduOegfM7YnKIp0Y001S07ffEcv/zNo7Gg6wAZwLtW2/+eUkRj8PLEyYDyU2NiwD7stAzhz50AjTbLojRyZdrEo6xu+f43xFNqf78Ix8mEKFr0ZRVVkkNRifa4niXPDdzIUiv5UZUGjW0ybFKdM3zm6xjEwMwo8ixu/IbAn74PqC7nypllCvLjKLFeYmYN24oYaVKWIRhQuGL3m98eQWFiVUL40palHtgcy5tffg8UOyAOqg5OF2kGVeyPZNmjq/jVHYyBUtBaMvrTLUlOKRRC3I+aW9tXs7aqclQytOiFQxq+aEapB8CAwEAAaNQME4wHQYDVR0OBBYEFA9Ub7RIfw21Qgbnf4IA3n4jUpAlMB8GA1UdIwQYMBaAFA9Ub7RIfw21Qgbnf4IA3n4jUpAlMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBAGBHECvs8V3xBKGRvNfBaTbY2FpbwLheSm3MUM4/hswvje24oknoHMF3dFNVnosOLXYdaRf8s0rsJfYuoUTap9tKzv0osGoA3mMw18LYW3a+mUHurx+kJZP+VN3emk84TXiX44CCendMVMxHxDQwg40YxALNc4uew2hlLReB8nC+55OlsIInIqPcIvtqUZgeNp2iecKnCgZPDaElez52GY5GRFszJd04sAQIrpg2+xfZvLMtvWwb9rpdto5oIdat2gIoMLdrmJUAYWP2+BLiKVpe9RtzfvqtQrk1lDoTj3adJYutNIPbTGOfI/Vux0HCw9KCrNTspdsfGTIQFJJi01E=",
                "SAML_SINGLE_SIGN_ON_REDIRECT_URL": "http://test-single-signon-url.test/",
            },
            id="SAML",
        ),
        pytest.param(
            IntegrationsState(
                smtp=SmtpRelationData(
                    host="smtp.example.com",
                    port=587,
                    user="testingusername",
                    password="testingpassword",
                    password_id=None,
                    auth_type=AuthType.PLAIN,
                    transport_security=TransportSecurity.STARTTLS,
                    domain="example.com",
                    skip_ssl_verify=False,
                )
            ),
            {
                "SMTP_AUTH_TYPE": "plain",
                "SMTP_DOMAIN": "example.com",
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PASSWORD": "testingpassword",
                "SMTP_PORT": "587",
                "SMTP_SKIP_SSL_VERIFY": "False",
                "SMTP_TRANSPORT_SECURITY": "starttls",
                "SMTP_USER": "testingusername",
            },
            id="SMTP",
        ),
        pytest.param(
            IntegrationsState(
                tracing=PaaSTracingRelationData(
                    endpoint="http://localhost:4318/tracing",
                    service_name="testing-application-name",
                )
            ),
            {
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318/tracing",
                "OTEL_SERVICE_NAME": "testing-application-name",
            },
            id="Tracing",
        ),
    ],
)
def test_generate_integration_environments(
    integrations: IntegrationsState, expected_env: dict[str, str]
):
    """
    arrange: given integration state.
    act: when _generate_integration_environments is called.
    assert: expected environment variables are populated.
    """
    charm_state = MagicMock()
    charm_state.integrations = integrations
    app = App(
        container=MagicMock(),
        charm_state=charm_state,
        workload_config=MagicMock(),
        database_migration=MagicMock(),
    )
    assert app._generate_integration_environments() == expected_env


@pytest.mark.parametrize(
    "integrations, expected_vars",
    _test_integrations_env_parameters(),
)
@pytest.mark.parametrize(
    "framework, container_mock",
    [
        pytest.param("flask", "flask_container_mock", id="flask"),
        pytest.param("django", "django_container_mock", id="django"),
        pytest.param("go", "go_container_mock", id="go"),
        pytest.param("expressjs", "expressjs_container_mock", id="expressjs"),
        pytest.param("fastapi", "fastapi_container_mock", id="fastapi"),
    ],
)
def test_integrations_env(
    monkeypatch,
    database_migration_mock,
    container_mock,
    integrations,
    framework,
    expected_vars,
    request,
):
    """
    arrange: prepare charmstate with integrations state.
    act: generate an app environment.
    assert: app environment generated should contain the expected env vars.
    """
    charm_state = CharmState(
        framework=framework,
        secret_key="foobar",
        is_secret_storage_ready=True,
        integrations=integrations,
    )
    workload_config = create_workload_config(
        framework_name=framework,
        unit_name=f"{framework}/0",
        state_dir=pathlib.Path(f"/tmp/{framework}/state"),
    )
    if framework == ("flask" or "django"):
        webserver = GunicornWebserver(
            webserver_config=WebserverConfig(),
            workload_config=workload_config,
            container=request.getfixturevalue(container_mock),
        )
        app = WsgiApp(
            container=request.getfixturevalue(container_mock),
            charm_state=charm_state,
            workload_config=workload_config,
            webserver=webserver,
            database_migration=database_migration_mock,
        )
    else:
        app = App(
            container=unittest.mock.MagicMock(),
            charm_state=charm_state,
            workload_config=workload_config,
            database_migration=unittest.mock.MagicMock(),
        )
    env = app.gen_environment()
    for expected_var_name, expected_env_value in expected_vars.items():
        assert expected_var_name in env
        assert env[expected_var_name] == expected_env_value


@pytest.mark.parametrize(
    "requires, expected_type",
    [
        pytest.param({}, NoneType, id="empty"),
        pytest.param(
            {
                "smtp": RelationMeta(
                    role=RelationRole.requires,
                    relation_name="smtp",
                    raw={"interface": "smtp", "limit": 1},
                )
            },
            SmtpRequires,
            id="smtp",
        ),
    ],
)
def test_init_smtp(requires, expected_type):
    """
    arrange: Get the mock requires.
    act: Run the _init_smtp function.
    assert: It should return SmtpRequires when there is smtp integration, none otherwise.
    """
    charm = unittest.mock.MagicMock()
    result = paas_charm.charm.PaasCharm._init_smtp(self=charm, requires=requires)
    assert isinstance(result, expected_type)


@pytest.mark.parametrize(
    "requires, expected_type",
    [
        pytest.param({}, NoneType, id="empty"),
        pytest.param(
            {
                "openfga": RelationMeta(
                    role=RelationRole.requires,
                    relation_name="openfga",
                    raw={"interface": "openfga", "limit": 1},
                )
            },
            OpenFGARequires,
            id="openfga",
        ),
    ],
)
def test_init_openfga(requires, expected_type):
    """
    arrange: Get the mock requires.
    act: Run the _init_openfga function.
    assert: It should return OpenfgaRequires when there is openfga integration, none otherwise.
    """
    charm = unittest.mock.MagicMock()
    result = paas_charm.charm.PaasCharm._init_openfga(self=charm, requires=requires)
    assert isinstance(result, expected_type)


def _test_missing_required_other_integrations_parameters():
    charm_without_relation = unittest.mock.MagicMock()
    charm_with_saml = unittest.mock.MagicMock()
    charm_with_tracing = unittest.mock.MagicMock()
    charm_with_smtp = unittest.mock.MagicMock()

    charm_state_without_relation = unittest.mock.MagicMock()
    charm_state_with_saml = unittest.mock.MagicMock()
    charm_state_with_tracing = unittest.mock.MagicMock()
    charm_state_with_smtp = unittest.mock.MagicMock()

    optional_saml_requires = {
        "saml": RelationMeta(
            role=RelationRole.requires,
            relation_name="saml",
            raw={"interface": "saml", "optional": True, "limit": 1},
        )
    }
    not_optional_saml_requires = {
        "saml": RelationMeta(
            role=RelationRole.requires,
            relation_name="saml",
            raw={"interface": "saml", "optional": False, "limit": 1},
        )
    }

    optional_tracing_requires = {
        "tracing": RelationMeta(
            role=RelationRole.requires,
            relation_name="tracing",
            raw={"interface": "tracing", "optional": True, "limit": 1},
        )
    }
    not_optional_tracing_requires = {
        "tracing": RelationMeta(
            role=RelationRole.requires,
            relation_name="tracing",
            raw={"interface": "tracing", "optional": False, "limit": 1},
        )
    }

    optional_smtp_requires = {
        "smtp": RelationMeta(
            role=RelationRole.requires,
            relation_name="smtp",
            raw={"interface": "smtp", "optional": True, "limit": 1},
        )
    }
    not_optional_smtp_requires = {
        "smtp": RelationMeta(
            role=RelationRole.requires,
            relation_name="smtp",
            raw={"interface": "smtp", "optional": False, "limit": 1},
        )
    }
    charm_with_saml._saml.return_value = True
    charm_with_tracing._tracing.return_value = True
    charm_with_smtp._smtp.return_value = True

    charm_state_with_saml.integrations.return_value.saml_parameters.return_value = True
    charm_state_with_tracing.integrations.return_value.tempo_parameters.return_value = True
    charm_state_with_smtp.integrations.return_value.smtp_parameters.return_value = True

    return [
        pytest.param(
            charm_with_saml,
            not_optional_saml_requires,
            charm_state_without_relation,
            "saml",
            id="missing not optional saml",
        ),
        pytest.param(
            charm_with_saml,
            optional_saml_requires,
            charm_state_without_relation,
            "",
            id="missing optional saml",
        ),
        pytest.param(
            charm_with_saml,
            not_optional_saml_requires,
            charm_state_with_saml,
            "",
            id="not missing not optional saml",
        ),
        pytest.param(
            charm_with_saml,
            optional_saml_requires,
            charm_state_with_saml,
            "",
            id="not missing optional saml",
        ),
        pytest.param(
            charm_with_tracing,
            not_optional_tracing_requires,
            charm_state_without_relation,
            "tracing",
            id="missing not optional tracing",
        ),
        pytest.param(
            charm_with_tracing,
            optional_tracing_requires,
            charm_state_without_relation,
            "",
            id="missing optional tracing",
        ),
        pytest.param(
            charm_with_tracing,
            not_optional_tracing_requires,
            charm_state_with_tracing,
            "",
            id="not missing not optional tracing",
        ),
        pytest.param(
            charm_with_tracing,
            optional_tracing_requires,
            charm_state_with_tracing,
            "",
            id="not missing optional tracing",
        ),
        pytest.param(
            charm_with_smtp,
            not_optional_smtp_requires,
            charm_state_without_relation,
            "smtp",
            id="missing not optional smtp",
        ),
        pytest.param(
            charm_with_smtp,
            optional_smtp_requires,
            charm_state_without_relation,
            "",
            id="missing optional smtp",
        ),
        pytest.param(
            charm_with_smtp,
            not_optional_smtp_requires,
            charm_state_with_smtp,
            "",
            id="not missing not optional smtp",
        ),
        pytest.param(
            charm_with_smtp,
            optional_smtp_requires,
            charm_state_with_smtp,
            "",
            id="not missing optional smtp",
        ),
        pytest.param(
            charm_without_relation,
            {},
            charm_state_without_relation,
            "",
            id="no relation",
        ),
    ]


@pytest.mark.skip(reason="TODO: This test is incomplete")
@pytest.mark.parametrize(
    "mock_charm, mock_requires, mock_charm_state, expected",
    _test_missing_required_other_integrations_parameters(),
)
def test_missing_required_other_integrations(
    mock_charm, mock_requires, mock_charm_state, expected
):
    """
    arrange: Get the mock charm, requires and charm state.
    act: Run the _missing_required_other_integrations function.
    assert: integration name should be in the result only when integration is required
     and the parameters for that integration not generated.
    """
    result = paas_charm.charm.PaasCharm._missing_required_other_integrations(
        mock_charm, mock_requires, mock_charm_state
    )
    assert result == expected


@pytest.mark.parametrize(
    "app_harness, framework, container_name",
    [
        pytest.param("flask_harness", "flask", FLASK_CONTAINER_NAME, id="flask"),
        pytest.param("django_harness", "django", DJANGO_CONTAINER_NAME, id="django"),
        pytest.param(
            "fastapi_harness",
            "fastapi",
            FASTAPI_CONTAINER_NAME,
            id="fastapi",
        ),
        pytest.param("go_harness", "go", GO_CONTAINER_NAME, id="go"),
        pytest.param("expressjs_harness", "expressjs", EXPRESSJS_CONTAINER_NAME, id="expressjs"),
    ],
)
def test_smtp_relation(
    app_harness: str,
    framework: str,
    container_name: str,
    request: pytest.FixtureRequest,
):
    """
    arrange: Integrate the charm with the smtp-integrator charm.
    act: Run all initial hooks.
    assert: The app service should have the environment variables related to smtp.
    """
    harness = request.getfixturevalue(app_harness)
    harness.add_relation(
        "smtp",
        "smtp-integrator",
        app_data=SMTP_RELATION_DATA_EXAMPLE,
    )
    container = harness.model.unit.get_container(container_name)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ActiveStatus()
    service_env = container.get_plan().services[framework].environment
    assert service_env.get("SMTP_AUTH_TYPE") is None
    assert service_env["SMTP_DOMAIN"] == SMTP_RELATION_DATA_EXAMPLE["domain"]
    assert service_env["SMTP_HOST"] == SMTP_RELATION_DATA_EXAMPLE["host"]
    assert service_env["SMTP_PORT"] == SMTP_RELATION_DATA_EXAMPLE["port"]
    assert service_env["SMTP_SKIP_SSL_VERIFY"] == SMTP_RELATION_DATA_EXAMPLE["skip_ssl_verify"]
    assert service_env.get("SMTP_TRANSPORT_SECURITY") is None


@pytest.mark.parametrize(
    "app_harness, framework, container_name",
    [
        pytest.param("flask_harness", "flask", FLASK_CONTAINER_NAME, id="flask"),
        pytest.param("django_harness", "django", DJANGO_CONTAINER_NAME, id="django"),
        pytest.param(
            "fastapi_harness",
            "fastapi",
            FASTAPI_CONTAINER_NAME,
            id="fastapi",
        ),
        pytest.param("go_harness", "go", GO_CONTAINER_NAME, id="go"),
        pytest.param("expressjs_harness", "expressjs", EXPRESSJS_CONTAINER_NAME, id="expressjs"),
    ],
)
def test_smtp_not_activated(
    app_harness: str,
    framework: str,
    container_name: str,
    request: pytest.FixtureRequest,
):
    """
    arrange: Deploy the charm without a relation to the smtp-integrator charm.
    act: Run all initial hooks.
    assert: The app service should not have the environment variables related to smtp.
    """
    harness = request.getfixturevalue(app_harness)
    container = harness.model.unit.get_container(container_name)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ActiveStatus()
    service_env = container.get_plan().services[framework].environment
    assert service_env.get("SMTP_AUTH_TYPE") is None
    assert service_env.get("SMTP_DOMAIN") is None
    assert service_env.get("SMTP_HOST") is None
    assert service_env.get("SMTP_PORT") is None
    assert service_env.get("SMTP_SKIP_SSL_VERIFY") is None
    assert service_env.get("SMTP_TRANSPORT_SECURITY") is None


@pytest.mark.parametrize(
    "app_harness, framework, container_name",
    [
        pytest.param("flask_harness", "flask", FLASK_CONTAINER_NAME, id="flask"),
        pytest.param("django_harness", "django", DJANGO_CONTAINER_NAME, id="django"),
        pytest.param(
            "fastapi_harness",
            "fastapi",
            FASTAPI_CONTAINER_NAME,
            id="fastapi",
        ),
        pytest.param("go_harness", "go", GO_CONTAINER_NAME, id="go"),
        pytest.param("expressjs_harness", "expressjs", EXPRESSJS_CONTAINER_NAME, id="expressjs"),
    ],
)
def test_openfga_relation(
    app_harness: str,
    framework: str,
    container_name: str,
    request: pytest.FixtureRequest,
):
    """
    arrange: Integrate the charm with the openfga charm.
    act: Run all initial hooks.
    assert: The app service should have the environment variables related to openfga.
    """
    harness = request.getfixturevalue(app_harness)
    harness.add_relation(
        "openfga",
        "openfga",
        app_data=OPENFGA_RELATION_DATA_EXAMPLE,
    )
    container = harness.model.unit.get_container(container_name)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ActiveStatus()
    service_env = container.get_plan().services[framework].environment
    assert service_env["FGA_STORE_ID"] == OPENFGA_RELATION_DATA_EXAMPLE["store_id"]
    assert service_env["FGA_TOKEN"] == OPENFGA_RELATION_DATA_EXAMPLE["token"]
    assert service_env["FGA_GRPC_API_URL"] == OPENFGA_RELATION_DATA_EXAMPLE["grpc_api_url"]
    assert service_env["FGA_HTTP_API_URL"] == OPENFGA_RELATION_DATA_EXAMPLE["http_api_url"]


@pytest.mark.parametrize(
    "app_harness, framework, container_name",
    [
        pytest.param("flask_harness", "flask", FLASK_CONTAINER_NAME, id="flask"),
        pytest.param("django_harness", "django", DJANGO_CONTAINER_NAME, id="django"),
        pytest.param(
            "fastapi_harness",
            "fastapi",
            FASTAPI_CONTAINER_NAME,
            id="fastapi",
        ),
        pytest.param("go_harness", "go", GO_CONTAINER_NAME, id="go"),
        pytest.param("expressjs_harness", "expressjs", EXPRESSJS_CONTAINER_NAME, id="expressjs"),
    ],
)
def test_openfga_not_activated(
    app_harness: str,
    framework: str,
    container_name: str,
    request: pytest.FixtureRequest,
):
    """
    arrange: Deploy the charm without a relation to the openfga charm.
    act: Run all initial hooks.
    assert: The app service should not have the environment variables related to openfga.
    """
    harness = request.getfixturevalue(app_harness)
    container = harness.model.unit.get_container(container_name)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ActiveStatus()
    service_env = container.get_plan().services[framework].environment
    assert service_env.get("FGA_STORE_ID") is None
    assert service_env.get("FGA_TOKEN") is None
    assert service_env.get("FGA_GRPC_API_URL") is None
    assert service_env.get("FGA_HTTP_API_URL") is None


@pytest.mark.parametrize(
    "app_harness",
    ["flask_harness", "django_harness", "fastapi_harness", "go_harness", "expressjs_harness"],
)
def test_secret_storage_relation_departed_hook(
    app_harness: str,
    request: pytest.FixtureRequest,
):
    """
    arrange: Run initial hooks. Add a unit to the secret-storage relation.
    act: Remove one unit from the secret-storage relation.
    assert: The restart function should be called once.
    """
    harness = request.getfixturevalue(app_harness)
    harness.begin_with_initial_hooks()
    harness.charm.restart = unittest.mock.MagicMock()
    peer_relation_name = "secret-storage"
    rel_id = harness.model.get_relation(peer_relation_name).id
    harness.add_relation_unit(rel_id, f"{harness._meta.name}/1")

    harness.charm.restart.reset_mock()
    harness.remove_relation_unit(rel_id, f"{harness._meta.name}/1")

    harness.charm.restart.assert_called_once()
