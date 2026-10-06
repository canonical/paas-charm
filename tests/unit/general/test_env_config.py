# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for explicit config environment variable mappings."""

import io
import json
from unittest.mock import MagicMock

import pytest
import yaml
from ops import testing
from pydantic import BaseModel, Field, ValidationError

from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState, framework_config_option_names
from paas_charm.exceptions import PaasConfigError
from paas_charm.fastapi.app import FastAPIApp
from paas_charm.paas_config import ConfigOptions, LoggingFormat, PaasConfig, read_paas_config
from paas_charm.springboot.charm import SpringBootApp


@pytest.fixture(name="make_app")
def make_app_fixture(tmp_path):
    """Build an app with controlled config sources and relation outputs."""

    def make_app(config, mappings, *, app_class=App, relations=None, framework=None):
        state = CharmState(
            framework="test",
            is_secret_key_ready=True,
            secret_key="generated-key",
            user_defined_config=config,
            framework_config=framework,
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
        app._generate_integration_environments = MagicMock(return_value=relations or {})
        return app

    return make_app


@pytest.mark.parametrize(
    "value, expected", [("text", "text"), (False, "false"), (0, "0"), (1.5, "1.5"), ("", "")]
)
def test_scalar_mapping(make_app, value, expected):
    """Rename a scalar without changing its value encoding or applying a prefix."""
    app = make_app({"log_level": value, "other": "keep"}, {"log-level": "custom.name"})
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


@pytest.mark.parametrize("app_class", [App, FastAPIApp, SpringBootApp])
def test_relations_after_framework_adjustments(make_app, app_class):
    """Relations have higher priority than built-in framework generation."""
    env = make_app(
        {},
        {},
        app_class=app_class,
        relations={
            "PYTHONPATH": "relation-path",
            "server.forward-headers-strategy": "relation-setting",
        },
    ).gen_environment()
    assert env["PYTHONPATH"] == "relation-path"
    assert env["server.forward-headers-strategy"] == "relation-setting"


@pytest.mark.parametrize("destination", ["", "A=B", "A\0B"])
def test_invalid_destinations(destination):
    """Reject names that cannot represent environment variable destinations."""
    with pytest.raises(ValidationError, match="Invalid environment variable name") as exc_info:
        ConfigOptions(options={"option": {"env-var": destination}})
    message = str(exc_info.value)
    assert "paas-config.yaml" in message
    assert "non-empty" in message
    assert "'='" in message and "NUL" in message


@pytest.mark.parametrize(
    "destination", ["spring.option", "with spaces", "lower-case", "\u00e9", "1"]
)
def test_verbatim_destinations(make_app, destination):
    """Allow arbitrary non-empty destination names except NUL and equals."""
    assert (
        make_app({"option": "value"}, {"option": destination}).gen_environment()[destination]
        == "value"
    )


def test_duplicate_destinations():
    """Reject duplicate destinations across scalar and secret sources."""
    with pytest.raises(ValidationError, match="mapped from both"):
        ConfigOptions(
            options={
                "one": {"env-var": "TARGET"},
                "secret": {"secret-env-vars": {"key": "TARGET"}},
            }
        )


@pytest.mark.parametrize(
    "mapping, options, unsupported",
    [
        ({"unknown": {"env-var": "TARGET"}}, {}, set()),
        ({"owned": {"env-var": "TARGET"}}, {"owned": {"type": "string"}}, {"owned"}),
        ({"secret": {"env-var": "TARGET"}}, {"secret": {"type": "secret"}}, set()),
        (
            {"scalar": {"secret-env-vars": {"key": "TARGET"}}},
            {"scalar": {"type": "string"}},
            set(),
        ),
        (
            {"foo-bar": {"env-var": "TARGET"}},
            {"foo-bar": {"type": "string"}, "foo_bar": {"type": "string"}},
            set(),
        ),
    ],
)
def test_invalid_sources(mapping, options, unsupported):
    """Reject unknown, framework-owned and incorrectly shaped sources."""
    with pytest.raises(PaasConfigError):
        ConfigOptions(options=mapping).validate_sources(options, unsupported)


def test_ambiguous_source_diagnostic():
    """Name both conflicting charm configuration options and explain the restriction."""
    with pytest.raises(PaasConfigError) as exc_info:
        ConfigOptions(options={"foo_bar": {"env-var": "TARGET"}}).validate_sources(
            {"foo-bar": {"type": "string"}, "foo_bar": {"type": "string"}}, set()
        )
    message = str(exc_info.value)
    assert "paas-config.yaml" in message
    assert "'foo-bar'" in message and "'foo_bar'" in message
    assert "hyphens and underscores" in message


@pytest.mark.parametrize(
    "content, expected_path, incorrect_name",
    [
        (
            "config:\n  options:\n    foo_bar:\n      env-var: 123\n",
            "config.options.foo_bar",
            "foo-bar",
        ),
        (
            "config:\n  options:\n    credentials:\n      secret-env-vars:\n        api_key: 123\n",
            "api_key",
            "api-key",
        ),
    ],
)
def test_schema_diagnostic_preserves_source_names(
    tmp_path, caplog, content, expected_path, incorrect_name
):
    """Preserve exact option names and secret content keys in schema diagnostics."""
    (tmp_path / "paas-config.yaml").write_text(content)
    with pytest.raises(PaasConfigError) as exc_info:
        read_paas_config(tmp_path)
    assert expected_path in str(exc_info.value)
    assert expected_path in caplog.text
    assert incorrect_name not in str(exc_info.value)
    assert incorrect_name not in caplog.text


def test_valid_sources():
    """Validate mappings using declared types rather than current option values."""
    ConfigOptions(
        options={
            "scalar": {"env-var": "TARGET"},
            "secret": {"secret-env-vars": {"name": "NAME"}},
        }
    ).validate_sources({"scalar": {"type": "string"}, "secret": {"type": "secret"}}, set())


def test_framework_config_option_names():
    """Use the same normalized field names and aliases for filtering and validation."""

    class Config(BaseModel):
        internal_name: str = Field(alias="public-option")
        port: int

    assert framework_config_option_names(Config) == {"internal_name", "public_option", "port"}


@pytest.mark.parametrize(
    "charm_class, option",
    [(GoCharm, "port"), (ExpressJSCharm, "port"), (FlaskCharm, "flask-debug")],
)
def test_framework_source_rejected_on_initialization(context_factory, charm_class, option):
    """Reject prefixed and unprefixed framework-owned sources in real charm initialization."""
    context = context_factory(
        charm_class, paas_config=PaasConfig(config={"options": {option: {"env-var": "TARGET"}}})
    )
    config_path = context.charm_root / "charmcraft.yaml"
    metadata = yaml.safe_load(config_path.read_text())
    metadata["config"]["options"].setdefault(option, {"type": "int", "default": 8080})
    config_path.write_text(yaml.safe_dump(metadata))
    with testing.Context(charm_class, meta=metadata, charm_root=context.charm_root) as declared:
        with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
            declared.run(declared.on.config_changed(), testing.State())
    assert isinstance(exc_info.value.__cause__, PaasConfigError)
    assert f"cannot map framework-owned option {option!r}" in str(exc_info.value.__cause__)


@pytest.mark.parametrize(
    "content, expected",
    [
        (
            "config:\n  options:\n    option: {env-var: A}\n    option: {env-var: B}\n",
            {"option": {"env-var": "B"}},
        ),
        (
            "config:\n  options:\n    option:\n      env-var: A\n      env-var: B\n",
            {"option": {"env-var": "B"}},
        ),
        (
            "config:\n  options:\n    secret:\n      secret-env-vars:\n        key: A\n        key: B\n",
            {"secret": {"secret-env-vars": {"key": "B"}}},
        ),
    ],
)
def test_duplicate_yaml_keys_keep_last_value(tmp_path, content, expected):
    """Retain the existing YAML loading behavior for repeated mapping keys."""
    (tmp_path / "paas-config.yaml").write_text(content)
    assert read_paas_config(tmp_path).config.model_dump(by_alias=True) == {"options": expected}


def test_yaml_merge_keys(tmp_path):
    """Continue supporting standard YAML anchors and merges."""
    (tmp_path / "paas-config.yaml").write_text(
        "config: &configuration\n"
        "  options:\n"
        "    option: {env-var: TARGET}\n"
        "<<:\n"
        "  config: *configuration\n"
    )
    assert read_paas_config(tmp_path).config.model_dump(by_alias=True) == {
        "options": {"option": {"env-var": "TARGET"}}
    }


def test_yaml_loader_rejects_python_objects(tmp_path):
    """Continue rejecting Python object tags when loading YAML."""
    (tmp_path / "paas-config.yaml").write_text("config: !!python/object:builtins.object {}\n")
    with pytest.raises(PaasConfigError, match="could not determine a constructor"):
        read_paas_config(tmp_path)


@pytest.mark.parametrize(
    "config",
    [
        {"unknown": {}},
        {"options": {"option": "TARGET"}},
        {"options": {"option": {}}},
        {"options": {"option": {"env-var": None}}},
        {"options": {"option": {"env-var": 123}}},
        {"options": {"option": {"secret-env-vars": None}}},
        {"options": {"secret": {"secret-env-vars": {"key": None}}}},
        {"options": {"secret": {"secret-env-vars": {"key": {"name": "TARGET"}}}}},
        {"options": {"option": {"env-name": "TARGET"}}},
        {"options": {"option": {"env-var": "TARGET", "secret-env-vars": {"key": "OTHER"}}}},
        {"options": {"option": {"env-var": "TARGET", "value-format": "json"}}},
    ],
)
def test_invalid_mapping_schema(config):
    """Reject unknown fields, non-string names and unsupported future settings."""
    with pytest.raises(ValidationError):
        PaasConfig(config=config)


def test_old_env_config_schema_rejected():
    """Reject the replaced proposal rather than silently ignoring its mappings."""
    with pytest.raises(ValidationError):
        PaasConfig(env={"config": {"option": "TARGET"}})


def test_unmapped_unset_behavior(make_app):
    """Leave legacy null encoding unchanged for unmapped config sources."""
    assert make_app({"option": None}, {}).gen_environment()["APP_OPTION"] == "null"


def test_underscore_source_name(make_app):
    """Match exact option names containing underscores without reversing normalization."""
    env = make_app({"foo_bar": "value"}, {"foo_bar": "TARGET"}).gen_environment()
    assert env["TARGET"] == "value"
    assert "APP_FOO_BAR" not in env


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


def test_flask_secret_mapping(context_factory, flask_framework_state):
    """Exercise secret mapping from charm configuration through reconciliation to Pebble."""
    context = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(
            config={"options": {"secret-test": {"secret-env-vars": {"foo": "TOKEN"}}}}
        ),
    )
    secret = testing.Secret(tracked_content={"foo": "configured-token", "bar": "keep"})
    state = testing.State(
        **{
            **flask_framework_state,
            "secrets": [*flask_framework_state["secrets"], secret],
            "config": {"secret-test": secret.id},
        }
    )
    out = context.run(context.on.config_changed(), state)
    env = out.get_container("app").plan.services["flask"].environment
    assert env["TOKEN"] == "configured-token"
    assert env["FLASK_SECRET_TEST_BAR"] == "keep"
    assert "FLASK_SECRET_TEST_FOO" not in env
