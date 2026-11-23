# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the env templates of paas-config.yaml."""

# pylint: disable=protected-access

import enum
from unittest.mock import MagicMock

import pytest
import yaml
from dpcharmlibs.interfaces import ValkeyResponseModel
from ops import testing
from pydantic import BaseModel, SecretStr

from examples.django.charm.src.charm import DjangoCharm
from paas_charm import env_templates
from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState, IntegrationsState
from paas_charm.env_templates import Reference
from paas_charm.exceptions import PaasConfigError
from paas_charm.oauth import PaaSOAuthRelationData
from paas_charm.paas_config import CONFIG_FILE_NAME, PaasConfig, read_paas_config
from paas_charm.rabbitmq import PaaSRabbitMQRelationData
from paas_charm.relations import CustomRelation
from paas_charm.s3 import PaaSS3RelationData, S3Relation
from paas_charm.tracing import PaaSTracingRelationData
from paas_charm.valkey import ValkeyRelation
from tests.unit.flask.constants import SMTP_RELATION_DATA_EXAMPLE


@pytest.mark.parametrize(
    "template, expected",
    [
        pytest.param("plain", ["plain"], id="literal"),
        pytest.param("a$$b", ["a", "$", "b"], id="escaped-dollar"),
        pytest.param(
            "x${pg.host}y",
            ["x", Reference("pg", "host", None), "y"],
            id="reference",
        ),
        pytest.param(
            "${pg.host:-localhost}", [Reference("pg", "host", "localhost")], id="default"
        ),
        pytest.param("${pg.host:-}", [Reference("pg", "host", "")], id="empty-default"),
        pytest.param(
            "${config.creds.user}", [Reference("config", "creds.user", None)], id="nested-field"
        ),
        pytest.param(
            "${http-proxy.no_proxy}",
            [Reference("http-proxy", "no_proxy", None)],
            id="hyphenated-namespace",
        ),
    ],
)
def test_parse(template, expected):
    """Split templates into literals and references."""
    assert env_templates.parse(template) == expected


@pytest.mark.parametrize(
    "template, diagnostic",
    [
        pytest.param("$HOME", "unexpected '$'", id="bare-variable"),
        pytest.param("cost: 5$", "unexpected '$'", id="trailing-dollar"),
        pytest.param("${nodot}", "invalid reference", id="no-field"),
        pytest.param("${}", "invalid reference", id="empty"),
        pytest.param("${a b.c}", "invalid reference", id="space"),
        pytest.param("${pg.host", "unexpected '$'", id="unterminated"),
    ],
)
def test_parse_invalid(template, diagnostic):
    """Reject malformed templates."""
    with pytest.raises(ValueError) as exc_info:
        env_templates.parse(template)
    assert diagnostic in str(exc_info.value)


def test_render():
    """Resolve references, apply defaults, and report unresolved references."""
    namespaces = {"pg": {"user": "u", "host": "h"}}
    assert env_templates.render("pg://${pg.user}@${pg.host}/$$", namespaces) == (
        "pg://u@h/$",
        [],
    )
    assert env_templates.render("${pg.port:-5432}", namespaces) == ("5432", [])
    assert env_templates.render("${pg.port}-${mq.host}", namespaces) == (
        None,
        [Reference("pg", "port", None), Reference("mq", "host", None)],
    )


class _Colour(enum.Enum):
    """Test enum."""

    RED = "red"


class _Model(BaseModel):
    """Test model."""

    text: str = "t"
    number: int = 3
    flag: bool = False
    secret: SecretStr = SecretStr("s3cret")
    colour: _Colour = _Colour.RED
    items: list[str] = ["a", "b"]
    missing: str | None = None


def test_model_fields():
    """Convert model fields to strings, unwrapping secrets and dropping unset values."""
    assert env_templates.model_fields(_Model()) == {
        "text": "t",
        "number": "3",
        "flag": "false",
        "secret": "s3cret",
        "colour": "red",
        "items": '["a", "b"]',
    }
    assert env_templates.model_fields(None) == {}


def test_config_fields():
    """Expose secret content keys as nested fields."""
    assert env_templates.config_fields(
        {"level": "info", "debug": True, "creds": {"user": "u", "pass": "p"}, "unset": None}
    ) == {"level": "info", "debug": "true", "creds.user": "u", "creds.pass": "p"}


def test_env_fields():
    """Derive fields from default variables, using the first matching prefix."""
    assert env_templates.env_fields(
        {"VALKEY_DB_HOSTNAME": "h", "VALKEY_MODE": "m", "OTHER": "x"}, "VALKEY_DB_", "VALKEY_"
    ) == {"hostname": "h", "mode": "m"}


@pytest.mark.parametrize(
    "env, diagnostic",
    [
        pytest.param({"": "x"}, "invalid environment variable name", id="empty-name"),
        pytest.param({"A=B": "x"}, "invalid environment variable name", id="equals-name"),
        pytest.param({"A": "$x"}, "A: unexpected '$'", id="bad-template"),
        pytest.param({"A": 1}, "valid string", id="not-a-string"),
    ],
)
def test_paas_config_invalid(tmp_path, env, diagnostic):
    """Reject invalid names and malformed templates when reading paas-config.yaml."""
    (tmp_path / CONFIG_FILE_NAME).write_text(yaml.safe_dump({"env": env}), encoding="utf-8")
    with pytest.raises(PaasConfigError) as exc_info:
        read_paas_config(tmp_path)
    assert diagnostic in str(exc_info.value.__cause__)


OPTIONS = {"level": {"type": "string"}, "creds": {"type": "secret"}}


@pytest.mark.parametrize(
    "template, endpoints, diagnostic",
    [
        pytest.param("${redis.url}", {"pg"}, "unknown namespace 'redis'", id="unknown-namespace"),
        pytest.param("${app.host}", set(), "unknown field", id="unknown-app-field"),
        pytest.param("${config.nope}", set(), "unknown charm configuration", id="unknown-option"),
        pytest.param("${config.creds}", set(), "secret content key", id="secret-without-key"),
        pytest.param("${config.level.x}", set(), "isn't a secret", id="key-of-non-secret"),
        pytest.param("${app.name}", {"app"}, "ambiguous", id="ambiguous-app"),
        pytest.param("${config.level}", {"config"}, "ambiguous", id="ambiguous-config"),
    ],
)
def test_validate_env_templates_invalid(template, endpoints, diagnostic):
    """Reject references to unknown namespaces and fields."""
    with pytest.raises(PaasConfigError, match=diagnostic):
        env_templates.validate_env_templates(
            {"A": template}, endpoints=endpoints, config_options=OPTIONS
        )


def test_validate_env_templates_valid():
    """Accept known namespaces and fields, and ignore removals."""
    env_templates.validate_env_templates(
        {
            "A": "${pg.anything}${app.name}${app.base_url}${app.port}",
            "B": "${config.level}${config.creds.user}",
            "C": None,
        },
        endpoints={"pg"},
        config_options=OPTIONS,
    )


def test_charm_rejects_invalid_reference(context_factory, django_base_state):
    """Fail the charm when a template references an unknown namespace."""
    context = context_factory(DjangoCharm, paas_config=PaasConfig(env={"A": "${redis.url}"}))
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**django_base_state))
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert "env.A" in str(exc_info.value.__cause__)


def test_charm_environment(context_factory, charm_root, django_base_state):
    """Render templates over relation, app and config values into the workload environment."""
    paas_config = read_paas_config(charm_root(DjangoCharm)).model_copy(
        update={
            "env": {
                "DATABASE_URL": (
                    "postgres://${postgresql.username}:${postgresql.password}"
                    "@${postgresql.hostname}:${postgresql.port}/${postgresql.name}"
                ),
                "DB_URIS": "${postgresql.uris}",
                "APP": "${app.name} ${app.port}",
                "DEBUG": "${config.django-debug:-off}",
                "MAIL_HOST": "${smtp.host}:${smtp.port}",
                "NO_TRACING": "${tracing.endpoint}",
                "WITH_DEFAULT": "${tracing.endpoint:-none}",
                "POSTGRESQL_DB_HOSTNAME": "override",
                "POSTGRESQL_DB_PASSWORD": None,
                "DJANGO_BASE_URL": "${tracing.endpoint}",
            }
        }
    )
    smtp = testing.Relation(
        endpoint="smtp", interface="smtp", remote_app_data=SMTP_RELATION_DATA_EXAMPLE
    )
    django_base_state["relations"].append(smtp)
    context = context_factory(DjangoCharm, paas_config=paas_config)
    out = context.run(context.on.config_changed(), testing.State(**django_base_state))

    env = out.get_container("app").plan.services["django"].environment
    assert env["DATABASE_URL"] == (
        "postgres://test-username:test-password@test-postgresql:5432/django-k8s"
    )
    assert env["DB_URIS"] == (
        "postgresql://test-username:test-password@test-postgresql:5432/django-k8s"
    )
    assert env["APP"] == "django-k8s 8000"
    assert env["DEBUG"] == "off"
    assert env["MAIL_HOST"] == "test-ip:1025"
    assert "NO_TRACING" not in env
    assert env["WITH_DEFAULT"] == "none"
    assert env["POSTGRESQL_DB_HOSTNAME"] == "override"
    assert "POSTGRESQL_DB_PASSWORD" not in env
    # Unresolved templates keep the default variable.
    assert env["DJANGO_BASE_URL"] == "http://django-k8s.test-model:8000"
    assert env["POSTGRESQL_DB_USERNAME"] == "test-username"


def test_template_namespaces(tmp_path):
    """Expose every built-in relation and custom relation fields under their endpoint names."""
    custom = MagicMock(relation_name="s3")
    custom.template_fields.return_value = {"bucket": "b"}
    state = CharmState(
        framework="test",
        is_secret_key_ready=True,
        secret_key="key",
        app_name="test-app",
        integrations=IntegrationsState(
            rabbitmq=PaaSRabbitMQRelationData(
                vhost="/", port=5672, hostname="mq", username="u", password="p"
            ),
            tracing=PaaSTracingRelationData(endpoint="http://tempo:4318", service_name="svc"),
            oauth=PaaSOAuthRelationData(
                client_id="id",
                client_secret="secret",
                issuer_url="https://issuer",
                authorization_endpoint="https://issuer/auth",
                token_endpoint="https://issuer/token",
                userinfo_endpoint="https://issuer/userinfo",
                jwks_endpoint="https://issuer/jwks",
                scopes="openid",
                provider_name="oidc",
                redirect_uri="https://app/callback",
                user_name_attribute="sub",
            ),
        ),
        custom_relations=[custom],
        env_templates={
            "MQ": "${rabbitmq.connect_string} ${rabbitmq.hostname}",
            "TRACES": "${tracing.endpoint}",
            "OIDC": "${oidc.client_id}:${oidc.issuer_url}",
            "BUCKET": "${s3.bucket}",
            "NAME": "${app.name}",
        },
    )
    workload = WorkloadConfig(
        framework="test",
        port=8080,
        base_dir=tmp_path,
        app_dir=tmp_path,
        state_dir=tmp_path,
        service_name="test",
        unit_name="test/0",
    )
    app = App(
        container=MagicMock(),
        charm_state=state,
        workload_config=workload,
        database_migration=MagicMock(),
    )
    env = app.gen_environment()
    assert env["MQ"] == "amqp://u:p@mq:5672/%2F mq"
    assert env["TRACES"] == "http://tempo:4318/"
    assert env["OIDC"] == "id:https://issuer"
    assert env["BUCKET"] == "b"
    assert env["NAME"] == "test-app"


def test_custom_relation_default_template_fields():
    """Custom relations expose no template fields unless they override the method."""

    class _Relation(CustomRelation):
        """Test relation."""

        relation_name = "test"

        def setup(self, on_change):
            """Do nothing."""

    relation = _Relation.__new__(_Relation)
    assert not relation.template_fields()


def test_valkey_and_s3_template_fields():
    """Expose relation data fields and, for Valkey, the parts of the connection URL."""
    valkey = ValkeyRelation.__new__(ValkeyRelation)
    valkey._requirer = None
    assert valkey.template_fields() == {}
    valkey._requirer = MagicMock()
    valkey._requirer.to_relation_data.return_value = ValkeyResponseModel(
        endpoints="localhost:6379", username="u", password="p"
    )
    fields = valkey.template_fields()
    assert fields["connect_string"] == "valkey://u:p@localhost:6379"
    assert fields["hostname"] == "localhost"
    assert fields["password"] == "p"

    s3 = S3Relation.__new__(S3Relation)
    s3._requirer = None
    assert s3.template_fields() == {}
    s3._requirer = MagicMock()
    s3._requirer.to_relation_data.return_value = PaaSS3RelationData.model_validate(
        {"access-key": "ak", "secret-key": "sk", "bucket": "b"}
    )
    assert s3.template_fields()["bucket"] == "b"
    assert s3.template_fields()["access_key"] == "ak"
