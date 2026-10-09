# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for explicit config environment variable mappings."""

import io
import json
from unittest.mock import MagicMock

import pytest
from ops import testing
from pydantic import Field

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState
from paas_charm.exceptions import CharmConfigInvalidError, PaasConfigError
from paas_charm.fastapi.app import FastAPIApp
from paas_charm.fastapi.charm import FastAPIConfig
from paas_charm.paas_config import ConfigOptions, LoggingFormat, PaasConfig
from paas_charm.relations import CustomRelation
from paas_charm.springboot.charm import SpringBootApp


@pytest.fixture(name="make_app")
def make_app_fixture(tmp_path):
    """Build an app with controlled config sources and relation outputs."""

    def make_app(
        config,
        mappings,
        *,
        app_class=App,
        relations=None,
        framework=None,
        custom_relations=None,
        framework_fields=None,
    ):
        state = CharmState(
            framework="test",
            is_secret_key_ready=True,
            secret_key="generated-key",
            user_defined_config=config,
            framework_config=framework,
            framework_config_fields=framework_fields,
            custom_relations=custom_relations,
            config_options=ConfigOptions(
                options={
                    option: (
                        {"secret-env-vars": mapping}
                        if isinstance(mapping, dict)
                        else {"env-var": mapping}
                    )
                    for option, mapping in mappings.items()
                }
            ),
        )
        workload = WorkloadConfig(
            framework="test",
            port=8080,
            base_dir=tmp_path,
            app_dir=tmp_path,
            state_dir=tmp_path,
            service_name="test",
            unit_name="test/0",
            logging_format=LoggingFormat.JSON,
        )
        app = app_class(
            container=MagicMock(),
            charm_state=state,
            workload_config=workload,
            database_migration=MagicMock(),
        )
        if custom_relations is None:
            app._generate_integration_environments = MagicMock(return_value=relations or {})
        return app

    return make_app


@pytest.mark.parametrize(
    "option, value, expected",
    [
        ("log-level", "text", "text"),
        ("log-level", False, "false"),
        ("log-level", 0, "0"),
        ("log-level", 1.5, "1.5"),
        ("log-level", "", ""),
        ("log_level", "text", "text"),
    ],
)
def test_scalar_mapping(make_app, option, value, expected):
    """Rename a scalar without changing its value encoding or applying a prefix."""
    app = make_app({"log_level": value, "other": "keep"}, {option: "custom.name"})
    env = app.gen_environment()
    assert env["custom.name"] == expected
    assert "APP_LOG_LEVEL" not in env
    assert env["APP_OTHER"] == "keep"


def test_secret_mapping(make_app, caplog):
    """Map exact secret keys, retaining unmapped entries and warning on missing keys."""
    app = make_app(
        {"credentials": {"foo-bar": "private-value", "other": "keep"}},
        {"credentials": {"foo-bar": "TOKEN", "missing": "MISSING"}},
        relations={"MISSING": "relation-value"},
    )
    env = app.gen_environment()
    assert env["TOKEN"] == "private-value"
    assert env["APP_CREDENTIALS_OTHER"] == "keep"
    assert "APP_CREDENTIALS_FOO_BAR" not in env
    assert env["MISSING"] == "relation-value"
    assert "credentials" in caplog.text
    assert "secret content key 'missing'" in caplog.text
    assert "environment variable 'MISSING'" in caplog.text
    assert "private-value" not in caplog.text


@pytest.mark.parametrize("mapping", ["TARGET", {"value": "TARGET"}])
def test_unset_mapping(make_app, mapping):
    """Unset mapped sources do not overwrite relation values or emit null outputs."""
    env = make_app(
        {"option": None}, {"option": mapping}, relations={"TARGET": "relation"}
    ).gen_environment()
    assert env["TARGET"] == "relation"
    assert "APP_OPTION" not in env
    assert make_app({"option": None}, {}).gen_environment()["APP_OPTION"] == "null"


def test_mapping_precedence(make_app, caplog):
    """Explicit mappings override relations, framework fields and generated variables."""
    app = make_app(
        {"option": "configured-value"},
        {"option": "METRICS_PORT"},
        framework={"metrics_port": 1111},
        relations={"METRICS_PORT": "2222", "APP_OPTION": "independent-output"},
    )
    env = app.gen_environment()
    assert env["METRICS_PORT"] == "configured-value"
    assert env["APP_OPTION"] == "independent-output"
    assert "option" in caplog.text and "METRICS_PORT" in caplog.text
    assert "configured-value" not in caplog.text


@pytest.mark.parametrize(
    "value, expected", [("configured-value", "configured-value"), (None, "relation-value")]
)
def test_mapping_precedence_over_custom_relations(make_app, caplog, value, expected):
    """Mappings override custom relation outputs only when their source is set."""
    relation = MagicMock(spec=CustomRelation)
    relation.relation_name = "custom"
    relation.gen_environment.return_value = {"TARGET": "relation-value"}
    app = make_app(
        {"option": value},
        {"option": "TARGET"},
        custom_relations=[relation],
    )

    env = app.gen_environment()

    assert env["TARGET"] == expected
    assert "APP_OPTION" not in env
    relation.gen_environment.assert_called_once_with()
    assert ("Explicit config.options mapping" in caplog.text) == (value is not None)
    assert "configured-value" not in caplog.text
    assert "relation-value" not in caplog.text


@pytest.mark.parametrize(
    "config, framework, destination",
    [
        ({"option": "config-private"}, {}, "APP_OPTION"),
        ({}, {"option": "framework-private"}, "OPTION"),
        ({}, {}, "METRICS_PORT"),
    ],
)
def test_integration_collision_warning(make_app, caplog, config, framework, destination):
    """Warn without values when integration output replaces the config/framework layer."""
    env = make_app(
        config,
        {},
        framework=framework,
        relations={destination: "relation-private", "UNIQUE": "unique-private"},
    ).gen_environment()
    assert env[destination] == "relation-private"
    assert env["UNIQUE"] == "unique-private"
    assert len(caplog.records) == 1
    assert destination in caplog.text
    assert "for a relation or Prometheus metrics" in caplog.text
    assert "charm configuration or framework settings" in caplog.text
    assert "private" not in caplog.text


def test_simultaneous_renames(make_app):
    """Swapping config destinations does not overwrite either source value."""
    env = make_app(
        {"one": "first", "two": "second"}, {"one": "APP_TWO", "two": "APP_ONE"}
    ).gen_environment()
    assert env["APP_ONE"] == "second"
    assert env["APP_TWO"] == "first"


@pytest.mark.parametrize(
    "app_class, destination",
    [
        (FastAPIApp, "UVICORN_LOG_CONFIG"),
        (FastAPIApp, "PYTHONPATH"),
        (SpringBootApp, "server.forward-headers-strategy"),
    ],
)
def test_mapping_after_framework_adjustments(make_app, app_class, destination):
    """Framework-specific adjustments cannot overwrite explicit mapped destinations."""
    env = make_app(
        {"option": "override"}, {"option": destination}, app_class=app_class
    ).gen_environment()
    assert env[destination] == "override"


@pytest.mark.parametrize(
    "app_class, destination",
    [(FastAPIApp, "PYTHONPATH"), (SpringBootApp, "server.forward-headers-strategy")],
)
def test_relations_after_framework_adjustments(make_app, app_class, destination):
    """Relations have higher priority than built-in framework generation."""
    env = make_app(
        {},
        {},
        app_class=app_class,
        relations={destination: "relation-value"},
    ).gen_environment()
    assert env[destination] == "relation-value"


@pytest.mark.parametrize(
    "destination", ["spring.option", "with spaces", "lower-case", "\u00e9", "1"]
)
def test_verbatim_destinations(make_app, destination):
    """Allow arbitrary non-empty destination names except NUL and equals."""
    assert (
        make_app({"option": "value"}, {"option": destination}).gen_environment()[destination]
        == "value"
    )


@pytest.mark.parametrize("value, expected", [(0, "0"), ("", "")])
def test_framework_mapping_swaps_and_precedence(make_app, value, expected):
    """Capture both original framework values before applying relation and config overrides."""
    app = make_app(
        {},
        {"public-one": "TWO", "public_two": "ONE"},
        framework={"one": value, "two": False},
        framework_fields={"public-one": "one", "public_two": "two"},
        relations={"ONE": "relation"},
    )
    env = app.gen_environment()
    assert env["ONE"] == "false"
    assert env["TWO"] == expected


def test_framework_secret_missing_key_keeps_default(make_app, caplog):
    """A missing entry does not remove the unmapped effective secret-key output."""
    env = make_app(
        {},
        {"app-secret-key": {"missing": "TARGET"}},
        framework_fields={"app-secret-key": "app_secret_key"},
    ).gen_environment()
    assert env["APP_SECRET_KEY"] == "generated-key"
    assert "TARGET" not in env
    assert "secret content key 'missing'" in caplog.text
    assert "generated-key" not in caplog.text


@pytest.mark.parametrize(
    "mapping, remaining",
    [
        pytest.param({"username": "DB_USER"}, {"password": "opaque"}, id="partial"),
        pytest.param({"username": "DB_USER", "password": "DB_PASSWORD"}, None, id="complete"),
        pytest.param(
            {"missing": "TARGET"}, {"username": "alice", "password": "opaque"}, id="missing"
        ),
    ],
)
def test_framework_secret_dictionary_mapping(make_app, caplog, mapping, remaining):
    """Map actual secret entries and preserve unmapped content in the original JSON output."""
    app = make_app(
        {},
        {"credentials": mapping},
        framework={"credentials": {"username": "alice", "password": "opaque"}},
        framework_fields={"credentials": "credentials"},
    )
    env = app.gen_environment()
    assert env.get("CREDENTIALS") == (json.dumps(remaining) if remaining else None)
    assert env.get("DB_USER") == ("alice" if "username" in mapping else None)
    assert env.get("DB_PASSWORD") == ("opaque" if "password" in mapping else None)
    assert "TARGET" not in env
    assert "alice" not in caplog.text
    assert "opaque" not in caplog.text
    assert app._charm_state.framework_config["credentials"] == {
        "username": "alice",
        "password": "opaque",
    }


def test_service_and_migration_environments(make_app):
    """Use mapped outputs consistently for services, workers, schedulers and migrations."""
    app = make_app({"option": False}, {"option": "TARGET"})
    app._container.pull.return_value = io.StringIO(
        json.dumps(
            {
                "test": {"command": "test"},
                "test-worker": {"command": "worker"},
                "test-scheduler": {"command": "scheduler"},
            }
        )
    )
    layer = app._app_layer()
    for service in layer["services"].values():
        assert service["environment"]["TARGET"] == "false"
        assert "APP_OPTION" not in service["environment"]
    app._run_migrations()
    env = app._database_migration.run.call_args.kwargs["environment"]
    assert env["TARGET"] == "false"
    assert "APP_OPTION" not in env


@pytest.mark.parametrize(
    "option, declarations, config, expected",
    [
        (
            "uvicorn-port",
            {
                "uvicorn-port": {"type": "int", "default": 9000},
                "webserver-port": {"type": "int", "default": 8000},
            },
            {},
            "9000",
        ),
        ("custom-metrics-port", {"custom-metrics-port": {"type": "int"}}, {}, "relation"),
        (
            "custom-metrics-port",
            {"custom-metrics-port": {"type": "int"}},
            {"custom-metrics-port": 5000},
            "5000",
        ),
    ],
    ids=["independent-input", "unset-field-keeps-generated-metrics", "configured-field"],
)
def test_framework_source_ownership(
    context_factory, framework_state_factory, monkeypatch, option, declarations, config, expected
):
    """Never map an ignored input or a library-generated variable as a framework source."""

    class Config(FastAPIConfig):
        metrics_port: int | None = Field(default=None, alias="custom-metrics-port")

    monkeypatch.setattr(FastAPICharm, "framework_config_class", Config)
    monkeypatch.setattr(
        FastAPIApp,
        "_generate_integration_environments",
        lambda self, prefix="": {"TARGET": "relation"},
    )
    context = context_factory(
        FastAPICharm,
        paas_config=PaasConfig(config={"options": {option: {"env-var": "TARGET"}}}),
        config_options=declarations,
    )
    state = framework_state_factory(FastAPICharm, config=config)
    out = context.run(context.on.config_changed(), testing.State(**state))
    assert out.unit_status == testing.ActiveStatus()
    env = next(iter(out.get_container("app").plan.services.values())).environment
    assert env["TARGET"] == expected
    assert env["METRICS_PORT"] == "8000"
    assert env["UVICORN_PORT"] == "8000"


@pytest.mark.parametrize("mapped", [False, True], ids=["unmapped", "mapped"])
@pytest.mark.parametrize(
    "charm_class, option, value, expected",
    [
        pytest.param(
            FlaskCharm,
            "application-root",
            "/foo",
            {"FLASK_APPLICATION_ROOT": None},
            id="flask",
        ),
        pytest.param(DjangoCharm, "debug", False, {"DJANGO_DEBUG": None}, id="django"),
        pytest.param(
            FastAPICharm,
            "uvicorn-port",
            9000,
            {"APP_UVICORN_PORT": None, "UVICORN_PORT": "8000"},
            id="fastapi",
        ),
        pytest.param(
            GoCharm,
            "app_secret_key",
            "user-key",
            {"APP_APP_SECRET_KEY": None, "APP_SECRET_KEY": "test"},
            id="go",
        ),
        pytest.param(
            ExpressJSCharm,
            "node_env",
            "development",
            {"APP_NODE_ENV": None, "NODE_ENV": "production"},
            id="expressjs",
        ),
        pytest.param(
            SpringBootCharm,
            "secret-key",
            "user-key",
            {"APP_SECRET_KEY": "test"},
            id="springboot",
        ),
    ],
)
def test_user_config_framework_field_protection(
    context_factory,
    framework_state_factory,
    charm_class,
    option,
    value,
    expected,
    mapped,
):
    """Suppress independent user defaults without losing their explicitly mapped values."""
    option_types = {str: "string", bool: "boolean", int: "int"}
    declarations = {option: {"type": option_types[type(value)]}}
    if option in ("app_secret_key", "node_env"):
        # Remove the real alias to keep the independent underscore source unambiguous.
        declarations[option.replace("_", "-")] = None
    context = context_factory(
        charm_class,
        paas_config=PaasConfig(
            config={"options": {option: {"env-var": "TARGET"}} if mapped else {}}
        ),
        config_options=declarations,
    )
    state = framework_state_factory(charm_class, config={option: value})
    out = context.run(context.on.config_changed(), testing.State(**state))
    assert out.unit_status == testing.ActiveStatus()
    env = next(iter(out.get_container("app").plan.services.values())).environment
    mapped_value = value if isinstance(value, str) else json.dumps(value)
    assert env.get("TARGET") == (mapped_value if mapped else None)
    for name, default in expected.items():
        assert env.get(name) == default


@pytest.mark.parametrize(
    "framework_value", [None, "/framework"], ids=["undeclared-alias", "configured-framework"]
)
def test_flask_application_root_protection(
    context_factory,
    framework_state_factory,
    framework_value,
):
    """Protect optional fields even without declared aliases, and preserve configured values."""
    declarations = {"application-root": {"type": "string"}}
    config = {"application-root": "/foo"}
    if framework_value is None:
        declarations["flask-application-root"] = None
    else:
        config["flask-application-root"] = framework_value
    context = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(),
        config_options=declarations,
    )
    out = context.run(
        context.on.config_changed(),
        testing.State(**framework_state_factory(FlaskCharm, config=config)),
    )
    assert out.unit_status == testing.ActiveStatus()
    env = out.get_container("app").plan.services["flask"].environment
    assert env.get("FLASK_APPLICATION_ROOT") == framework_value


def test_protected_user_secret_partial_mapping(context_factory, framework_state_factory):
    """Keep suppressed defaults suppressed while mapping an independent secret's selected entry."""
    context = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(
            config={"options": {"secret-key": {"secret-env-vars": {"token": "TOKEN"}}}}
        ),
        config_options={"secret-key": {"type": "secret"}},
    )
    secret = testing.Secret(tracked_content={"token": "mapped-token", "unmapped": "keep"})
    state = framework_state_factory(FlaskCharm, config={"secret-key": secret.id})
    state["secrets"].append(secret)
    out = context.run(context.on.config_changed(), testing.State(**state))
    assert out.unit_status == testing.ActiveStatus()
    env = next(iter(out.get_container("app").plan.services.values())).environment
    assert env["TOKEN"] == "mapped-token"
    assert env["FLASK_SECRET_KEY"] == "test"
    assert "FLASK_SECRET_KEY_TOKEN" not in env
    assert "FLASK_SECRET_KEY_UNMAPPED" not in env


@pytest.mark.parametrize(
    "charm_class, option",
    [(GoCharm, "port"), (FastAPICharm, "webserver-host"), (FlaskCharm, "webserver-workers")],
)
def test_non_environment_sources_rejected(context_factory, charm_class, option):
    """Reject settings without declared config options or configuration environment outputs."""
    context = context_factory(
        charm_class, paas_config=PaasConfig(config={"options": {option: {"env-var": "TARGET"}}})
    )
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State())
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert repr(option) in str(exc_info.value.__cause__)


@pytest.mark.parametrize(
    "charm_class, option, config, expected, original_names",
    [
        (FlaskCharm, "flask-debug", {"flask-debug": False}, "false", ("FLASK_DEBUG",)),
        (
            FlaskCharm,
            "flask-preferred-url-scheme",
            {"flask-preferred-url-scheme": "https"},
            "HTTPS",
            ("FLASK_PREFERRED_URL_SCHEME",),
        ),
        (
            DjangoCharm,
            "django-allowed-hosts",
            {"django-allowed-hosts": "a.example,b.example"},
            json.dumps(["a.example", "b.example", "django-k8s.test-model"]),
            ("DJANGO_ALLOWED_HOSTS",),
        ),
        (FastAPICharm, "webserver-workers", {}, "1", ("WEB_CONCURRENCY",)),
        (
            FastAPICharm,
            "webserver-log-level",
            {"webserver-log-level": "debug"},
            "debug",
            ("UVICORN_LOG_LEVEL",),
        ),
        (ExpressJSCharm, "node-env", {}, "production", ("NODE_ENV",)),
        (
            SpringBootCharm,
            "app-profiles",
            {"app-profiles": "dev,prod"},
            "dev,prod",
            ("APP_PROFILES", "spring.profiles.active"),
        ),
        (SpringBootCharm, "app-profiles", {}, None, ("APP_PROFILES", "spring.profiles.active")),
    ],
)
def test_framework_option_mapping(
    context_factory, framework_state_factory, charm_class, option, config, expected, original_names
):
    """Rename real framework outputs without changing defaults, validation or encoding."""
    context = context_factory(
        charm_class, paas_config=PaasConfig(config={"options": {option: {"env-var": "TARGET"}}})
    )
    out = context.run(
        context.on.config_changed(),
        testing.State(**framework_state_factory(charm_class, config=config)),
    )
    assert out.unit_status == testing.ActiveStatus()
    services = out.get_container("app").plan.services
    env = next(iter(services.values())).environment
    if expected is None:
        assert "TARGET" not in env
    else:
        assert env["TARGET"] == expected
    assert not set(original_names) & env.keys()


@pytest.mark.parametrize("configured", [False, True])
@pytest.mark.parametrize(
    "charm_class, original_names",
    [
        (FlaskCharm, ("FLASK_SECRET_KEY",)),
        (DjangoCharm, ("DJANGO_SECRET_KEY",)),
        (FastAPICharm, ("APP_SECRET_KEY",)),
        (ExpressJSCharm, ("APP_SECRET_KEY",)),
        (GoCharm, ("APP_SECRET_KEY",)),
        (SpringBootCharm, ("SECRET_KEY", "APP_SECRET_KEY")),
    ],
)
def test_framework_secret_key_mapping(
    context_factory, framework_state_factory, charm_class, original_names, configured, caplog
):
    """Rename the configured or generated secret key consistently across all frameworks."""
    context = context_factory(
        charm_class,
        paas_config=PaasConfig(
            config={
                "options": {"app-secret-key": {"secret-env-vars": {"value": "SESSION_SECRET"}}}
            }
        ),
    )
    state = framework_state_factory(charm_class)
    if configured:
        secret = testing.Secret(tracked_content={"value": "configured-key"})
        state["secrets"].append(secret)
        state["config"]["app-secret-key"] = secret.id
    out = context.run(context.on.config_changed(), testing.State(**state))
    assert out.unit_status == testing.ActiveStatus()
    services = out.get_container("app").plan.services
    for service in services.values():
        assert service.environment["SESSION_SECRET"] == (
            "configured-key" if configured else "test"
        )
        assert not set(original_names) & service.environment.keys()
    assert "configured-key" not in caplog.text


@pytest.mark.parametrize(
    "charm_class, option, value",
    [(SpringBootCharm, "app-profiles", ""), (FastAPICharm, "webserver-workers", 0)],
)
def test_mapping_preserves_framework_validation(
    context_factory, framework_state_factory, charm_class, option, value
):
    """Renaming an output does not make invalid framework setting values acceptable."""
    context = context_factory(
        charm_class, paas_config=PaasConfig(config={"options": {option: {"env-var": "TARGET"}}})
    )
    state = framework_state_factory(charm_class, config={option: value})
    with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
        context.run(context.on.config_changed(), testing.State(**state))
    assert isinstance(exc_info.value.__cause__, CharmConfigInvalidError)


@pytest.mark.parametrize("configured", [False, True])
def test_framework_secret_rotation(
    context_factory, framework_state_factory, monkeypatch, configured
):
    """Mapped keys follow both configured-secret updates and generated-key rotation."""
    context = context_factory(
        GoCharm,
        paas_config=PaasConfig(
            config={
                "options": {"app-secret-key": {"secret-env-vars": {"value": "SESSION_SECRET"}}}
            }
        ),
    )
    state = framework_state_factory(GoCharm)
    if configured:
        secret = testing.Secret(
            tracked_content={"value": "old-key"}, latest_content={"value": "rotated-key"}
        )
        state["secrets"].append(secret)
        state["config"]["app-secret-key"] = secret.id
        out = context.run(context.on.secret_changed(secret), testing.State(**state))
    else:
        out = context.run(context.on.config_changed(), testing.State(**state))
        monkeypatch.setattr("paas_charm.secret_key.secrets.token_urlsafe", lambda _: "rotated-key")
        out = context.run(context.on.action("rotate-secret-key"), out)
    env = next(iter(out.get_container("app").plan.services.values())).environment
    assert env["SESSION_SECRET"] == "rotated-key"
    assert "APP_SECRET_KEY" not in env


def test_declared_config_default_is_mapped(context_factory, flask_framework_state):
    """Map the declared option default when the operator has not configured a value."""
    context = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(
            config={"options": {"oidc-redirect-path": {"env-var": "REDIRECT_PATH"}}}
        ),
    )
    out = context.run(context.on.config_changed(), testing.State(**flask_framework_state))
    env = out.get_container("app").plan.services["flask"].environment
    assert env["REDIRECT_PATH"] == "/callback"
    assert "FLASK_OIDC_REDIRECT_PATH" not in env
