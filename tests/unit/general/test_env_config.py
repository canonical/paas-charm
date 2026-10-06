# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for explicit config environment variable mappings."""

import io
import json
from unittest.mock import MagicMock

import pytest
from ops import testing
from pydantic import ValidationError

from examples.flask.charm.src.charm import FlaskCharm
from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState
from paas_charm.exceptions import PaasConfigError
from paas_charm.fastapi.app import FastAPIApp
from paas_charm.paas_config import EnvConfig, LoggingFormat, PaasConfig, read_paas_config
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
            env_config=EnvConfig(config=mappings),
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
    assert "missing" in caplog.text
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
    with pytest.raises(ValidationError, match="Invalid environment variable name"):
        EnvConfig(config={"option": destination})


@pytest.mark.parametrize(
    "destination", ["spring.option", "with spaces", "lower-case", "\u00e9", "1"]
)
def test_verbatim_destinations(make_app, destination):
    """Allow arbitrary non-empty destination names except NUL and equals."""
    assert EnvConfig(config={"option": destination}).config["option"] == destination
    assert (
        make_app({"option": "value"}, {"option": destination}).gen_environment()[destination]
        == "value"
    )


def test_duplicate_destinations():
    """Reject duplicate destinations across scalar and secret sources."""
    with pytest.raises(ValidationError, match="mapped from both"):
        EnvConfig(config={"one": "TARGET", "secret": {"key": "TARGET"}})


@pytest.mark.parametrize(
    "mapping, options, unsupported",
    [
        ({"unknown": "TARGET"}, {}, set()),
        ({"owned": "TARGET"}, {"owned": {"type": "string"}}, {"owned"}),
        ({"secret": "TARGET"}, {"secret": {"type": "secret"}}, set()),
        ({"scalar": {"key": "TARGET"}}, {"scalar": {"type": "string"}}, set()),
        (
            {"foo-bar": "TARGET"},
            {"foo-bar": {"type": "string"}, "foo_bar": {"type": "string"}},
            set(),
        ),
    ],
)
def test_invalid_sources(mapping, options, unsupported):
    """Reject unknown, framework-owned and incorrectly shaped sources."""
    with pytest.raises(PaasConfigError):
        EnvConfig(config=mapping).validate_sources(options, unsupported)


def test_valid_sources():
    """Validate mappings using declared types rather than current option values."""
    EnvConfig(config={"scalar": "TARGET", "secret": {"name": "NAME"}}).validate_sources(
        {"scalar": {"type": "string"}, "secret": {"type": "secret"}}, set()
    )


@pytest.mark.parametrize(
    "content",
    [
        "env:\n  config:\n    option: A\n    option: B\n",
        "env:\n  config:\n    secret:\n      key: A\n      key: B\n",
    ],
)
def test_duplicate_yaml_keys(tmp_path, content):
    """Reject duplicate YAML keys instead of silently keeping the last mapping."""
    (tmp_path / "paas-config.yaml").write_text(content)
    with pytest.raises(PaasConfigError, match="duplicate mapping key"):
        read_paas_config(tmp_path)


def test_yaml_merge_keys(tmp_path):
    """Keep standard YAML anchor merging while rejecting explicit duplicate keys."""
    (tmp_path / "paas-config.yaml").write_text(
        "env: &environment\n" "  config:\n" "    option: TARGET\n" "<<:\n" "  env: *environment\n"
    )
    assert read_paas_config(tmp_path).env.config == {"option": "TARGET"}


def test_yaml_loader_rejects_python_objects(tmp_path):
    """Duplicate-key validation retains SafeLoader's rejection of Python object tags."""
    (tmp_path / "paas-config.yaml").write_text("env: !!python/object:builtins.object {}\n")
    with pytest.raises(PaasConfigError, match="could not determine a constructor"):
        read_paas_config(tmp_path)


@pytest.mark.parametrize(
    "env",
    [
        {"unknown": {}},
        {"config": {"option": 123}},
        {"config": {"secret": {"key": None}}},
        {"config": {"secret": {"key": {"name": "TARGET"}}}},
    ],
)
def test_invalid_mapping_schema(env):
    """Reject unknown fields, non-string names and unsupported future settings."""
    with pytest.raises(ValidationError):
        PaasConfig(env=env)


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


def test_flask_secret_mapping(context_factory, flask_framework_state):
    """Exercise secret mapping from image config through reconciliation to Pebble."""
    context = context_factory(
        FlaskCharm,
        paas_config=PaasConfig(env={"config": {"secret-test": {"foo": "TOKEN"}}}),
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
