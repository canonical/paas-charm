# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integrations unit tests."""
import itertools
import json
import unittest
from types import NoneType

import pytest
from ops.testing import Harness

from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm._gunicorn.wsgi_app import WsgiApp
from paas_charm.app import App, WorkloadConfig, map_integrations_to_env
from paas_charm.charm_state import (
    CharmState,
    IntegrationsState,
    RelationParam,
    S3Parameters,
    SamlParameters,
    SmtpParameters,
    TempoParameters,
    _create_config_attribute,
    generate_relation_parameters,
)
from paas_charm.exceptions import CharmConfigInvalidError
from tests.unit.flask.constants import (
    INTEGRATIONS_RELATION_DATA,
    SAML_APP_RELATION_DATA_EXAMPLE,
    SMTP_RELATION_DATA_EXAMPLE,
)
from tests.unit.general.conftest import MockTracingEndpointRequirer


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


@pytest.mark.parametrize(
    "relation_data, relation_parameter_type, accept_empty, expected_type, should_fail",
    [
        pytest.param(
            SAML_APP_RELATION_DATA_EXAMPLE,
            SamlParameters,
            True,
            SamlParameters,
            False,
            id="Saml correct parameters",
        ),
        pytest.param({}, SamlParameters, False, NoneType, False, id="Saml empty parameters"),
        pytest.param(
            {"wrong_key": "wrong_value"},
            SamlParameters,
            False,
            NoneType,
            True,
            id="Saml wrong parameters",
        ),
        pytest.param(
            INTEGRATIONS_RELATION_DATA["s3"]["app_data"],
            S3Parameters,
            False,
            S3Parameters,
            False,
            id="S3 correct parameters",
        ),
        pytest.param(
            {"wrong_key": "wrong_value"},
            S3Parameters,
            False,
            NoneType,
            True,
            id="S3 wrong parameters",
        ),
        pytest.param({}, S3Parameters, True, NoneType, True, id="S3 empty parameters"),
        pytest.param(
            {"service_name": "app_name", "endpoint": "localhost:1234"},
            TempoParameters,
            False,
            TempoParameters,
            False,
            id="Tempo correct parameters",
        ),
        pytest.param(
            {"wrong_key": "wrong_value"},
            TempoParameters,
            False,
            NoneType,
            True,
            id="Tempo wrong parameters",
        ),
        pytest.param({}, TempoParameters, False, NoneType, False, id="Tempo empty parameters"),
        pytest.param(
            SMTP_RELATION_DATA_EXAMPLE,
            SmtpParameters,
            False,
            SmtpParameters,
            False,
            id="Smtp correct parameters",
        ),
        pytest.param(
            {"wrong_key": "wrong_value"},
            SmtpParameters,
            False,
            NoneType,
            True,
            id="Smtp wrong parameters",
        ),
        pytest.param({}, SmtpParameters, True, NoneType, True, id="Smtp empty parameters"),
    ],
)
def test_generate_relation_parameters(
    relation_data: dict,
    relation_parameter_type: RelationParam,
    accept_empty: bool,
    expected_type: type,
    should_fail: bool,
):
    """
    arrange: None
    act: Generate a relation parameter object.
    assert: The function should error out or the resultant object should be the correct type.
    """
    if should_fail:
        with pytest.raises(CharmConfigInvalidError):
            relation_parameters = generate_relation_parameters(
                relation_data, relation_parameter_type, accept_empty
            )
    else:
        relation_parameters = generate_relation_parameters(
            relation_data, relation_parameter_type, accept_empty
        )
        assert isinstance(relation_parameters, expected_type)


def _test_integrations_state_build_parameters():
    mock_relations: dict[str, str] = {
        "redis_uri": None,
        "database_requirers": {},
        "s3_connection_info": None,
        "saml_relation_data": None,
        "rabbitmq_uri": None,
        "tracing_requirer": None,
        "app_name": None,
        "smtp_relation_data": None,
    }

    return [
        pytest.param(
            {**mock_relations, "saml_relation_data": SAML_APP_RELATION_DATA_EXAMPLE},
            False,
            id="Saml correct parameters",
        ),
        pytest.param(
            {**mock_relations, "saml_relation_data": {}},
            True,
            id="Saml empty parameters",
        ),
        pytest.param(
            {**mock_relations, "saml_relation_data": {"wrong_key": "wrong_value"}},
            True,
            id="Saml wrong parameters",
        ),
        pytest.param(
            {**mock_relations, "s3_connection_info": INTEGRATIONS_RELATION_DATA["s3"]["app_data"]},
            False,
            id="S3 correct parameters",
        ),
        pytest.param(
            {**mock_relations, "s3_connection_info": {}},
            False,
            id="S3 empty parameters",
        ),
        pytest.param(
            {**mock_relations, "s3_connection_info": {"wrong_key": "wrong_value"}},
            True,
            id="S3 wrong parameters",
        ),
        pytest.param(
            {
                **mock_relations,
                "tracing_requirer": MockTracingEndpointRequirer(True, "localhost:1234"),
                "app_name": "app_name",
            },
            False,
            id="Tempo correct parameters",
        ),
        pytest.param(
            {**mock_relations, "tracing_requirer": None},
            False,
            id="Tempo empty parameters",
        ),
        pytest.param(
            {**mock_relations, "tracing_requirer": MockTracingEndpointRequirer(False, "")},
            False,
            id="Tempo not ready",
        ),
        pytest.param(
            {**mock_relations, "smtp_relation_data": SMTP_RELATION_DATA_EXAMPLE},
            False,
            id="Smtp correct parameters",
        ),
        pytest.param(
            {**mock_relations, "smtp_relation_data": {}},
            False,
            id="Smtp empty parameters",
        ),
        pytest.param(
            {**mock_relations, "smtp_relation_data": {"wrong_key": "wrong_value"}},
            True,
            id="Smtp wrong parameters",
        ),
        pytest.param(
            {**mock_relations, "redis_uri": "http://redisuri"},
            False,
            id="Redis correct parameters",
        ),
        pytest.param(
            {**mock_relations, "redis_uri": ""},
            False,
            id="Redis empty parameters",
        ),
        pytest.param(
            {
                **mock_relations,
                "rabbitmq_uri": "amqp://test-app:3m036hhyiDHs@rabbitmq-k8s-endpoints.testing.svc.cluster.local:5672/",
            },
            False,
            id="RabbitMQ correct parameters",
        ),
        pytest.param(
            {**mock_relations, "rabbitmq_uri": "http://redisuri"},
            False,
            id="RabbitMQ empty parameters",
        ),
    ]


@pytest.mark.parametrize(
    "mock_relations, should_fail",
    _test_integrations_state_build_parameters(),
)
def test_integrations_state_build(
    mock_relations: dict,
    should_fail: bool,
):
    """
    arrange: None
    act: Generate a relation parameter object.
    assert: The function should error out or the resultant object should be the correct type.
    """
    if should_fail:
        with pytest.raises(CharmConfigInvalidError):
            IntegrationsState.build(
                redis_uri=mock_relations["redis_uri"],
                database_requirers=mock_relations["database_requirers"],
                s3_connection_info=mock_relations["s3_connection_info"],
                saml_relation_data=mock_relations["saml_relation_data"],
                rabbitmq_uri=mock_relations["rabbitmq_uri"],
                tracing_requirer=mock_relations["tracing_requirer"],
                app_name=mock_relations["app_name"],
                smtp_relation_data=mock_relations["smtp_relation_data"],
            )
    else:
        assert isinstance(
            IntegrationsState.build(
                redis_uri=mock_relations["redis_uri"],
                database_requirers=mock_relations["database_requirers"],
                s3_connection_info=mock_relations["s3_connection_info"],
                saml_relation_data=mock_relations["saml_relation_data"],
                rabbitmq_uri=mock_relations["rabbitmq_uri"],
                tracing_requirer=mock_relations["tracing_requirer"],
                app_name=mock_relations["app_name"],
                smtp_relation_data=mock_relations["smtp_relation_data"],
            ),
            IntegrationsState,
        )


def _test_integrations_env_parameters():

    parameters_with_empty_prefix = _generate_map_integrations_to_env_parameters()

    return [pytest.param(p.values[0], p.values[2], id=p.id) for p in parameters_with_empty_prefix]


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
    act: generate a flask environment.
    assert: flask_environment generated should contain the expected env vars.
    """
    charm_state = CharmState(
        framework=framework,
        secret_key="foobar",
        is_secret_storage_ready=True,
        integrations=integrations,
    )
    workload_config = create_workload_config(framework_name=framework, unit_name=f"{framework}/0")
    if framework == ("flask" or "django"):
        app = WsgiApp(
            container=request.getfixturevalue(container_mock),
            charm_state=charm_state,
            workload_config=workload_config,
            webserver=unittest.mock.MagicMock(),
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
