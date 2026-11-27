# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the env templates of paas-config.yaml."""

# pylint: disable=protected-access

import enum
import logging
from unittest.mock import MagicMock

import pytest
import yaml
from charms.squid_forward_proxy.v0.http_proxy import ProxyConfig
from dpcharmlibs.interfaces import ValkeyResponseModel
from jinja2.sandbox import ImmutableSandboxedEnvironment
from ops import testing
from pydantic import BaseModel, SecretStr

from examples.django.charm.src.charm import DjangoCharm
from examples.flask.charm.src.charm import FlaskCharm
from paas_charm import env_templates
from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState, IntegrationsState
from paas_charm.exceptions import PaasConfigError
from paas_charm.oauth import PaaSOAuthRelationData
from paas_charm.paas_config import (
    CONFIG_FILE_NAME,
    OAuthRelationConfig,
    PaasConfig,
    read_paas_config,
)
from paas_charm.rabbitmq import PaaSRabbitMQRelationData
from paas_charm.s3 import PaaSS3RelationData, S3Relation
from paas_charm.saml import PaaSSAMLRelationData, SamlRelation
from paas_charm.springboot.charm import SpringBootApp, SpringValkeyRelation
from paas_charm.tracing import PaaSTracingRelationData
from paas_charm.valkey import ValkeyRelation
from tests.unit.flask.constants import SMTP_RELATION_DATA_EXAMPLE


@pytest.mark.parametrize(
    "template",
    [
        "{{ config[app.name] }}",
        "{{ app.name() }}",
        "{{ app.port + 1 }}",
        "{{ app.name | upper }}",
        "{{ app.name | default(config.other) }}",
        "{% if app.name %}yes{% endif %}",
        "{{ app.name",
    ],
)
def test_parse_invalid(template):
    """Reject syntax outside the static Jinja subset."""
    with pytest.raises(ValueError):
        env_templates.parse(template)


def test_environment_sandbox():
    """Run templates in Jinja's immutable sandbox with no globals, tests, or extra filters."""
    assert isinstance(env_templates._ENV, ImmutableSandboxedEnvironment)
    assert not env_templates._ENV.globals
    assert not env_templates._ENV.tests
    assert set(env_templates._ENV.filters) == {"default"}


@pytest.mark.parametrize(
    "payload",
    [
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ ().__class__.__base__.__subclasses__() }}",
        "{{ cycler.__init__.__globals__.os.popen('id').read() }}",
        "{{ '{0.__class__}'.format(app.name) }}",
        "{{ '%s' | format(app.name) }}",
        "{{ app.name | attr('__class__') }}",
        "{{ app.name | default('x', true) }}",
        "{{ app.name | default('x', boolean=true) }}",
        "{{ app.name | default('a') | default('b') }}",
        "{{ app.name[0] }}",
        "{{ config[0] }}",
        "{% set x = config %}{{ x }}",
        "{% import 'x' as m %}",
        "{% include 'x' %}",
        "{% macro m() %}x{% endmacro %}",
    ],
)
def test_parse_rejects_ssti_and_unsafe_constructs(payload):
    """Reject SSTI payloads, statements, calls, format escapes, and unsafe filter arguments."""
    with pytest.raises(ValueError):
        env_templates.parse(payload)


@pytest.mark.parametrize(
    "path",
    [
        "config.__class__",
        "config.__class__.__mro__",
        "config.__init__.__globals__",
        "config.items",
        "config.keys",
        "app.name.__class__",
        "self._TemplateReference__context",
        "range",
        "dict",
        "cycler",
        "joiner",
        "lipsum",
        "namespace",
    ],
)
def test_render_blocks_python_attributes_and_globals(path):
    """Never resolve Python attributes, dunders, or Jinja globals even if render() is called directly."""
    namespaces = {"app": {"name": "demo"}, "config": {"token": "s3cret"}}
    assert env_templates.render("{{ " + path + " }}", namespaces) == (None, [path])
    assert env_templates.render("{{ " + path + " | default('blocked') }}", namespaces) == (
        "blocked",
        [],
    )


def test_secret_values_not_logged(context_factory, flask_base_state, caplog):
    """Never log secret values when overwriting, skipping unresolved templates, or rejecting NUL."""
    secret_value = "super-sensitive-secret-token"
    secret = testing.Secret(tracked_content={"token": secret_value})
    state = testing.State(
        **{
            **flask_base_state,
            "secrets": [secret],
            "config": {**flask_base_state.get("config", {}), "secret-test": secret.id},
        }
    )
    paas_config = PaasConfig(
        env={
            "FLASK_SECRET_KEY": "{{ config['secret-test'].token }}",
            "UNRESOLVED_WITH_SECRET": (
                "{{ config['secret-test'].token }}:{{ relations.tracing.endpoint }}"
            ),
        }
    )
    context = context_factory(FlaskCharm, paas_config=paas_config)
    with caplog.at_level(logging.DEBUG):
        out = context.run(context.on.config_changed(), state)

    env = out.get_container("app").plan.services["flask"].environment
    assert env["FLASK_SECRET_KEY"] == secret_value
    assert "UNRESOLVED_WITH_SECRET" not in env
    assert secret_value not in caplog.text

    nul_secret_value = f"{secret_value}\x00tail"
    nul_secret = testing.Secret(tracked_content={"token": nul_secret_value})
    nul_state = testing.State(
        **{
            **flask_base_state,
            "secrets": [nul_secret],
            "config": {**flask_base_state.get("config", {}), "secret-test": nul_secret.id},
        }
    )
    nul_context = context_factory(
        FlaskCharm, paas_config=PaasConfig(env={"API_TOKEN": "{{ config['secret-test'].token }}"})
    )
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        nul_context.run(nul_context.on.config_changed(), nul_state)
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert secret_value not in str(exc_info.value.__cause__)


def test_render():
    """Resolve references, apply defaults, and report unresolved references."""
    namespaces = {"relations": {"pg": {"items": "<u&p>", "empty": "", "unset": None}}}
    assert env_templates.render("{{ relations.pg.items }} $5\n", namespaces) == ("<u&p> $5\n", [])
    assert env_templates.render("{{ relations.pg.empty | default('x') }}", namespaces) == ("", [])
    assert env_templates.render("{{ relations.pg.unset | default('x') }}", namespaces) == ("x", [])
    assert env_templates.render("{{ relations.pg.unset }}", namespaces) == (
        None,
        ["relations.pg.unset"],
    )
    assert env_templates.render("{{ range | default('x') }}", {}) == ("x", [])
    assert env_templates.render("{{ relations.mq.items | default('$5') }}", namespaces) == (
        "$5",
        [],
    )
    assert env_templates.render(
        "{{ relations.pg.port }}-{{ relations.mq.host }}-{{ relations.pg.port }}", namespaces
    ) == (
        None,
        ["relations.pg.port", "relations.mq.host"],
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
    ) == {"level": "info", "debug": "true", "creds": {"user": "u", "pass": "p"}}


@pytest.mark.parametrize(
    "env, diagnostic",
    [
        pytest.param({"": "x"}, "invalid environment variable name", id="empty-name"),
        pytest.param({"A=B": "x"}, "invalid environment variable name", id="equals-name"),
        pytest.param({"A": "{{ config[app.name] }}"}, "A: expected a static", id="bad-template"),
        pytest.param({"A": 1}, "valid string", id="not-a-string"),
        pytest.param({"A": None}, "valid string", id="null-value"),
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
    "template, diagnostic",
    [
        ("{{ relations.redis.url }}", "unknown"),
        ("{{ relations.logging.url }}", "relation does not expose template fields"),
        ("{{ app.host }}", "unknown"),
        ("{{ config.creds }}", "secret option 'creds' requires one content key"),
        ("{{ config.creds.user.extra }}", "secret option 'creds' requires one content key"),
        ("{{ config.level.x }}", "option 'level' isn't a secret and cannot be indexed"),
        ("{{ relations }}", "unknown"),
    ],
)
def test_validate_env_templates_invalid(template, diagnostic):
    """Reject references to unknown namespaces and fields."""
    with pytest.raises(PaasConfigError, match=diagnostic):
        env_templates.validate_env_templates(
            {"A": template}, endpoints={"logging": set()}, config_options=OPTIONS
        )


def test_validate_env_templates_valid():
    """Accept known namespaces and fields."""
    env_templates.validate_env_templates(
        {
            "A": "{{ relations.app.host }}{{ app.name }}{{ app.base_url }}{{ app.port }}",
            "B": "{{ config.level }}{{ config.creds.user }}",
        },
        endpoints={"app": {"host"}},
        config_options=OPTIONS,
    )


@pytest.mark.parametrize(
    "option, hint", [("logl-level", ". Did you mean 'log-level'?"), ("unrelated", "")]
)
def test_unknown_config_with_default(option, hint):
    """Report the unknown option and suggest only a close metadata match despite a default."""
    source = "{{ config['" + option + "'] | default('info') }}"
    with pytest.raises(PaasConfigError) as exc_info:
        env_templates.validate_env_templates(
            {"LOG_LEVEL": source}, endpoints={}, config_options={"log-level": {"type": "string"}}
        )
    assert str(exc_info.value) == (
        f"paas-config.yaml: env.LOG_LEVEL: config.{option}: unknown charm configuration option {option!r}{hint}"
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "postgresql",
        "valkey",
        "s3",
        "saml",
        "smtp",
        "oidc",
        "openfga",
        "rabbitmq",
        "http-proxy",
        "tracing",
        "ingress",
        "peers",
    ],
)
def test_charm_rejects_invalid_reference(context_factory, flask_base_state, endpoint):
    """A default must not hide a misspelled built-in field, even on an absent relation."""
    template = "{{ relations['" + endpoint + "'].typo | default('ok') }}"
    context = context_factory(FlaskCharm, paas_config=PaasConfig(env={"A": template}))
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**flask_base_state))
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert "env.A" in str(exc_info.value.__cause__)
    assert "unknown built-in relation field" in str(exc_info.value.__cause__)


@pytest.mark.parametrize("endpoint", ["logging", "grafana-dashboard", "metrics-endpoint"])
def test_unsupported_endpoints_rejected_with_default(context_factory, flask_base_state, endpoint):
    """Reject observability endpoints that do not expose template fields, even with a default."""
    template = "{{ relations['" + endpoint + "'].url | default('ok') }}"
    context = context_factory(FlaskCharm, paas_config=PaasConfig(env={"A": template}))
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**flask_base_state))
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert "env.A" in str(exc_info.value.__cause__)


def test_ingress_and_peers_templates(context_factory, flask_base_state):
    """Expose relations.ingress.url and relations.peers.fqdns only when available."""
    paas_config = PaasConfig(
        env={
            "PUBLIC_URL": "{{ relations.ingress.url }}",
            "PUBLIC_URL_DEFAULT": "{{ relations.ingress.url | default('none') }}",
            "BASE_URL": "{{ app.base_url }}",
            "PEER_LIST": "{{ relations.peers.fqdns }}",
            "PEER_LIST_DEFAULT": "{{ relations.peers.fqdns | default('solo') }}",
        }
    )
    context = context_factory(FlaskCharm, paas_config=paas_config)

    out_absent = context.run(context.on.config_changed(), testing.State(**flask_base_state))
    env_absent = out_absent.get_container("app").plan.services["flask"].environment
    assert "PUBLIC_URL" not in env_absent
    assert env_absent["PUBLIC_URL_DEFAULT"] == "none"
    assert env_absent["BASE_URL"] == "http://flask-k8s.test-model:8000"
    assert "PEER_LIST" not in env_absent
    assert env_absent["PEER_LIST_DEFAULT"] == "solo"

    ingress = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "https://public.example.com/"}'},
    )
    peers = testing.PeerRelation(
        endpoint="peers",
        interface="peers",
        peers_data={2: {}, 1: {}},
    )
    relations = [r for r in flask_base_state["relations"] if r.endpoint != "peers"] + [
        ingress,
        peers,
    ]
    out_ready = context.run(
        context.on.relation_changed(ingress),
        testing.State(**{**flask_base_state, "relations": relations}),
    )
    env_ready = out_ready.get_container("app").plan.services["flask"].environment
    assert env_ready["PUBLIC_URL"] == "https://public.example.com/"
    assert env_ready["PUBLIC_URL_DEFAULT"] == "https://public.example.com/"
    assert env_ready["BASE_URL"] == "https://public.example.com/"
    assert env_ready["PEER_LIST"] == (
        "flask-k8s-1.flask-k8s-endpoints.test-model.svc.cluster.local,"
        "flask-k8s-2.flask-k8s-endpoints.test-model.svc.cluster.local"
    )
    assert env_ready["PEER_LIST_DEFAULT"] == env_ready["PEER_LIST"]


def test_charm_environment(context_factory, charm_root, django_base_state):
    """Render templates over relation, app and config values into the workload environment."""
    paas_config = read_paas_config(charm_root(DjangoCharm)).model_copy(
        update={
            "env": {
                "DATABASE_URL": (
                    "postgres://{{ relations.postgresql.username }}:{{ relations.postgresql.password }}"
                    "@{{ relations.postgresql.hostname }}:{{ relations.postgresql.port }}/{{ relations.postgresql.name }}"
                ),
                "DB_URIS": "{{ relations.postgresql.uris }}",
                "APP": "{{ app.name }} {{ app.port }}",
                "DEBUG": "{{ config['django-debug'] | default('off') }}",
                "MAIL_HOST": "{{ relations.smtp.host }}:{{ relations.smtp.port }}",
                "NO_TRACING": "{{ relations.tracing.endpoint }}",
                "WITH_DEFAULT": "{{ relations.tracing.endpoint | default('none') }}",
                "POSTGRESQL_DB_HOSTNAME": "override",
                "DJANGO_BASE_URL": "{{ relations.tracing.endpoint }}",
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
    # Unresolved templates keep the default variable.
    assert env["DJANGO_BASE_URL"] == "http://django-k8s.test-model:8000"
    assert env["POSTGRESQL_DB_USERNAME"] == "test-username"


def test_unbound_builtin_has_no_schema(context_factory, flask_base_state):
    """A built-in endpoint name alone does not bind a template schema."""
    context = context_factory(
        FlaskCharm,
        relation_interfaces={"tracing": "another_interface"},
        paas_config=PaasConfig(env={"TRACE": "{{ relations.tracing.endpoint | default('off') }}"}),
    )
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**flask_base_state))
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert "relation does not expose template fields" in str(exc_info.value.__cause__)


def test_rendered_nul_is_rejected(context_factory, flask_base_state):
    """Reject invalid process environment values without including the value in the error."""
    context = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(
            env={"TOKEN": r"{{ relations.tracing.endpoint | default('sensitive\x00text') }}"}
        ),
    )
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**flask_base_state))
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert (
        str(exc_info.value.__cause__) == "paas-config.yaml: env.TOKEN: rendered value contains NUL"
    )


def test_absent_relations(context_factory, flask_base_state):
    """Allow valid built-in fields before a provider is related."""
    context = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(
            env={
                "CACHE_HOST": "{{ relations.valkey.hostname | default('localhost') }}",
                "OAUTH_REDIRECT": "{{ relations.oidc.redirect_path | default('/default') }}",
                "OAUTH_REDIRECT_UNSET": "{{ relations.oidc.redirect_path }}",
            }
        ),
    )
    out = context.run(context.on.config_changed(), testing.State(**flask_base_state))
    env = out.get_container("app").plan.services["flask"].environment
    assert env["CACHE_HOST"] == "localhost"
    assert env["OAUTH_REDIRECT"] == "/default"
    assert "OAUTH_REDIRECT_UNSET" not in env


def test_custom_relation_rejected_in_templates(context_factory, flask_base_state):
    """Reject templates referencing author-defined custom relations."""
    context = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(
            env={
                "TEMPORAL": "{{ relations['temporal-host-info'].custom_field | default('offline') }}"
            }
        ),
    )
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**flask_base_state))
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert "relation does not expose template fields" in str(exc_info.value.__cause__)


def test_custom_subclass_of_builtin_excluded_from_templates(
    context_factory, flask_base_state, monkeypatch
):
    """An author subclass of a built-in relation is excluded from both validation and rendering."""
    called = False

    class _CustomS3(S3Relation):
        """Author-defined S3 override."""

        def setup(self, on_change) -> None:
            """Do nothing."""

        def template_fields(self) -> dict[str, str]:
            """Track whether template_fields is invoked."""
            nonlocal called
            called = True
            return {"bucket": "override"}

    monkeypatch.setattr(FlaskCharm, "custom_relations", [*FlaskCharm.custom_relations, _CustomS3])

    rejected = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(env={"BUCKET": "{{ relations.s3.bucket | default('none') }}"}),
    )
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        rejected.run(rejected.on.config_changed(), testing.State(**flask_base_state))
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert "relation does not expose template fields" in str(exc_info.value.__cause__)

    rendering = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(env={"LABEL": "{{ app.name }}"}),
    )
    out = rendering.run(rendering.on.config_changed(), testing.State(**flask_base_state))
    assert out.get_container("app").plan.services["flask"].environment["LABEL"] == "flask-k8s"
    assert not called


def test_template_namespaces(tmp_path):
    """Expose built-in relation fields under their endpoint names."""
    s3 = MagicMock(spec=S3Relation, relation_name="s3")
    s3.template_fields.return_value = {"bucket": "b"}
    s3.gen_environment.return_value = {}
    state = CharmState(
        framework="test",
        is_secret_key_ready=True,
        secret_key="key",
        app_name="test-app",
        integrations=IntegrationsState(
            http_proxy=ProxyConfig(http_proxy="http://p:3128", https_proxy="https://p:443"),
            rabbitmq=PaaSRabbitMQRelationData(
                vhost="/",
                port=5672,
                hostname="mq",
                username="u@",
                password="part/rest",
                hostnames=["mq2"],
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
        template_relations=[s3],
        oauth_config=OAuthRelationConfig(redirect_path="/auth/callback"),
        env_templates={
            "MQ": "{{ relations.rabbitmq.connect_string }} {{ relations.rabbitmq.hostname }}",
            "MQ_PASSWORD": "{{ relations.rabbitmq.password }}",
            "TRACES": "{{ relations.tracing.endpoint }}",
            "OIDC": "{{ relations.oidc.client_id }}:{{ relations.oidc.issuer_url }}",
            "OIDC_PATH": "{{ relations.oidc.redirect_path }}",
            "BUCKET": "{{ relations.s3.bucket }}",
            "NAME": "{{ app.name }}",
            "PROXIES": "{{ relations['http-proxy'].http_proxy }} {{ relations['http-proxy'].https_proxy }}",
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
    assert env["MQ"] == "amqp://u%40:part%2Frest@mq:5672/%2F mq"
    assert env["RABBITMQ_CONNECT_STRINGS"] == "amqp://u%40:part%2Frest@mq2:5672/%2F"
    assert env["MQ_PASSWORD"] == env["RABBITMQ_PASSWORD"] == "part/rest"
    assert env["TRACES"] == "http://tempo:4318/"
    assert env["OIDC"] == "id:https://issuer"
    assert env["OIDC_PATH"] == "/auth/callback"
    assert env["BUCKET"] == "b"
    assert env["NAME"] == "test-app"
    assert env["PROXIES"] == "http://p:3128 https://p:443"

    state.env_templates = {"LABEL": "{{ app.name }}"}
    spring = SpringBootApp(
        container=MagicMock(),
        charm_state=state,
        workload_config=workload,
        database_migration=MagicMock(),
    )
    assert spring.gen_environment()["LABEL"] == "test-app"


@pytest.mark.parametrize("relation_class", [ValkeyRelation, SpringValkeyRelation])
def test_valkey_template_fields(relation_class):
    """Expose the same URL parts and preserve missing fields across frameworks."""
    valkey = relation_class.__new__(relation_class)
    valkey._requirer = None
    assert valkey.template_fields() == {}
    valkey._requirer = MagicMock()
    valkey._requirer.to_relation_data.return_value = ValkeyResponseModel(
        endpoints="localhost:6379", username="u", password="p/@"
    )
    fields = valkey.template_fields()
    assert fields["connect_string"] == "valkey://u:p%2F%40@localhost:6379"
    assert fields["hostname"] == "localhost"
    assert fields["password"] == "p/@"
    assert env_templates.render(
        "{{ relations.valkey.mode | default('standalone') }}", {"relations": {"valkey": fields}}
    ) == (
        "standalone",
        [],
    )
    valkey._requirer.to_relation_data.return_value = ValkeyResponseModel(
        endpoints="localhost:6379", username="u"
    )
    fields = valkey.template_fields()
    assert fields["connect_string"] == "valkey://u@localhost:6379"
    assert env_templates.render(
        "{{ relations.valkey.password | default('fallback') }}", {"relations": {"valkey": fields}}
    ) == ("fallback", [])


def test_secret_config_templates(context_factory, flask_base_state):
    """Resolve secret config content keys when set and handle missing secrets or keys."""
    paas_config = PaasConfig(
        env={
            "API_TOKEN": "{{ config['secret-test'].token }}",
            "FALLBACK_TOKEN": "{{ config['secret-test'].missing | default('none') }}",
        }
    )
    context = context_factory(FlaskCharm, paas_config=paas_config)

    out_unset = context.run(context.on.config_changed(), testing.State(**flask_base_state))
    env_unset = out_unset.get_container("app").plan.services["flask"].environment
    assert "API_TOKEN" not in env_unset
    assert env_unset["FALLBACK_TOKEN"] == "none"

    secret = testing.Secret(tracked_content={"token": "s3cret-value"})
    state_with_secret = testing.State(
        **{
            **flask_base_state,
            "secrets": [secret],
            "config": {**flask_base_state.get("config", {}), "secret-test": secret.id},
        }
    )
    out_set = context.run(context.on.config_changed(), state_with_secret)
    env_set = out_set.get_container("app").plan.services["flask"].environment
    assert env_set["API_TOKEN"] == "s3cret-value"
    assert env_set["FALLBACK_TOKEN"] == "none"


def test_s3_template_fields():
    """Expose the S3 relation data fields."""
    s3 = S3Relation.__new__(S3Relation)
    s3._requirer = None
    assert s3.template_fields() == {}
    s3._requirer = MagicMock()
    s3._requirer.to_relation_data.return_value = PaaSS3RelationData.model_validate(
        {"access-key": "ak", "secret-key": "sk", "bucket": "b"}
    )
    assert s3.template_fields()["bucket"] == "b"
    assert s3.template_fields()["access_key"] == "ak"


def test_saml_template_fields():
    """Expose the SAML relation data fields."""
    saml = SamlRelation.__new__(SamlRelation)
    saml.get_relation_data = MagicMock(return_value=None)
    assert saml.template_fields() == {}
    saml.get_relation_data = MagicMock(
        return_value=PaaSSAMLRelationData(
            entity_id="https://idp.example.com",
            metadata_url="https://idp.example.com/metadata",
            certificates=("cert-data",),
            endpoints=(),
        )
    )
    fields = saml.template_fields()
    assert fields["entity_id"] == "https://idp.example.com"
    assert fields["metadata_url"] == "https://idp.example.com/metadata"
