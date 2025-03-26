# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integrations unit tests."""
import itertools
import json
import unittest
from types import NoneType

import pytest
from charms.smtp_integrator.v0.smtp import SmtpRequires
from ops import ActiveStatus, RelationMeta, RelationRole
from ops.testing import Harness

import paas_charm
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
from tests.unit.django.constants import DEFAULT_LAYER as DJANGO_DEFAULT_LAYER
from tests.unit.django.constants import DJANGO_CONTAINER_NAME
from tests.unit.fastapi.constants import DEFAULT_LAYER as FASTAPI_DEFAULT_LAYER
from tests.unit.fastapi.constants import FASTAPI_CONTAINER_NAME
from tests.unit.flask.constants import DEFAULT_LAYER as FLASK_DEFAULT_LAYER
from tests.unit.flask.constants import (
    FLASK_CONTAINER_NAME,
    INTEGRATIONS_RELATION_DATA,
    SAML_APP_RELATION_DATA_EXAMPLE,
    SMTP_RELATION_DATA_EXAMPLE,
)
from tests.unit.general.conftest import MockTracingEndpointRequirer
from tests.unit.go.constants import DEFAULT_LAYER as GO_DEFAULT_LAYER
from tests.unit.go.constants import GO_CONTAINER_NAME


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
    relation_dict: dict[str, str] = {
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
            {**relation_dict, "saml_relation_data": SAML_APP_RELATION_DATA_EXAMPLE},
            False,
            id="Saml correct parameters",
        ),
        pytest.param(
            {**relation_dict, "saml_relation_data": {}},
            True,
            id="Saml empty parameters",
        ),
        pytest.param(
            {**relation_dict, "saml_relation_data": {"wrong_key": "wrong_value"}},
            True,
            id="Saml wrong parameters",
        ),
        pytest.param(
            {**relation_dict, "s3_connection_info": INTEGRATIONS_RELATION_DATA["s3"]["app_data"]},
            False,
            id="S3 correct parameters",
        ),
        pytest.param(
            {**relation_dict, "s3_connection_info": {}},
            False,
            id="S3 empty parameters",
        ),
        pytest.param(
            {**relation_dict, "s3_connection_info": {"wrong_key": "wrong_value"}},
            True,
            id="S3 wrong parameters",
        ),
        pytest.param(
            {
                **relation_dict,
                "tracing_requirer": MockTracingEndpointRequirer(True, "localhost:1234"),
                "app_name": "app_name",
            },
            False,
            id="Tempo correct parameters",
        ),
        pytest.param(
            {**relation_dict, "tracing_requirer": None},
            False,
            id="Tempo empty parameters",
        ),
        pytest.param(
            {**relation_dict, "tracing_requirer": MockTracingEndpointRequirer(False, "")},
            False,
            id="Tempo not ready",
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
            {**relation_dict, "smtp_relation_data": {"wrong_key": "wrong_value"}},
            True,
            id="Smtp wrong parameters",
        ),
        pytest.param(
            {**relation_dict, "redis_uri": "http://redisuri"},
            False,
            id="Redis correct parameters",
        ),
        pytest.param(
            {**relation_dict, "redis_uri": ""},
            False,
            id="Redis empty parameters",
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
    ]


@pytest.mark.parametrize(
    "relation_dict, should_fail",
    _test_integrations_state_build_parameters(),
)
def test_integrations_state_build(
    relation_dict: dict,
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
                redis_uri=relation_dict["redis_uri"],
                database_requirers=relation_dict["database_requirers"],
                s3_connection_info=relation_dict["s3_connection_info"],
                saml_relation_data=relation_dict["saml_relation_data"],
                rabbitmq_uri=relation_dict["rabbitmq_uri"],
                tracing_requirer=relation_dict["tracing_requirer"],
                app_name=relation_dict["app_name"],
                smtp_relation_data=relation_dict["smtp_relation_data"],
            )
    else:
        assert isinstance(
            IntegrationsState.build(
                redis_uri=relation_dict["redis_uri"],
                database_requirers=relation_dict["database_requirers"],
                s3_connection_info=relation_dict["s3_connection_info"],
                saml_relation_data=relation_dict["saml_relation_data"],
                rabbitmq_uri=relation_dict["rabbitmq_uri"],
                tracing_requirer=relation_dict["tracing_requirer"],
                app_name=relation_dict["app_name"],
                smtp_relation_data=relation_dict["smtp_relation_data"],
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
    act: generate an app environment.
    assert: app environment generated should contain the expected env vars.
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
    expected = paas_charm.charm.PaasCharm._missing_required_other_integrations(
        mock_charm, mock_requires, mock_charm_state
    )


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
    "app_harness", ["flask_harness", "django_harness", "fastapi_harness", "go_harness"]
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
