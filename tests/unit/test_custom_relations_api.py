# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the public ``CustomRelation`` extension API."""

import copy
import pathlib

import pytest
from ops import testing

from tests.unit.test_custom_relations.src.charm import (
    ContextCharm,
    EnvVarCharm,
    InvalidDataCharm,
    OverwritingCharm,
    SideEffectCharm,
    reconcile_calls,
    setup_calls,
)

CONTAINER_NAME = "app"

# Base Pebble plan for the "test" framework charm (service name == framework name).
TEST_CUSTOM_LAYER = {
    "services": {
        "test": {
            "override": "replace",
            "startup": "enabled",
            "command": "test-command",
            "user": "_daemon_",
        }
    }
}


def _base_state(tmp_path: pathlib.Path) -> dict:
    """Return a leader state with a peer relation and the test workload container."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    return {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={"test_secret_key": "test"},
            ),
        ],
        "containers": {
            testing.Container(
                name=CONTAINER_NAME,
                can_connect=True,
                mounts={"app": testing.Mount(location="/app", source=app_dir)},
                _base_plan=copy.deepcopy(TEST_CUSTOM_LAYER),
            )
        },
        "model": testing.Model(name="test-model"),
    }


def _example_db_relation(uri: str | None) -> testing.Relation:
    """Build an ``example-db`` relation with the given ``uri`` in the app databag."""
    return testing.Relation(
        endpoint="example-db",
        interface="example_db",
        remote_app_data={"uri": uri} if uri is not None else {},
    )


def _invalid_db_relation(data: dict) -> testing.Relation:
    """Build an ``invalid-db`` relation with the given remote app databag."""
    return testing.Relation(
        endpoint="invalid-db",
        interface="invalid_db",
        remote_app_data=data,
    )


@pytest.fixture(autouse=True)
def _reset_call_recorders():
    """Clear the module-level call recorders before each test."""
    reconcile_calls.clear()
    setup_calls.clear()
    yield


@pytest.fixture
def envvar_context(context_factory) -> testing.Context:
    """Return a Context rooted at the env-var custom relation charm."""
    return context_factory(EnvVarCharm)


@pytest.fixture
def context_context(context_factory) -> testing.Context:
    """Return a Context rooted at the context inspection charm."""
    return context_factory(ContextCharm)


@pytest.fixture
def invalid_context(context_factory) -> testing.Context:
    """Return a Context rooted at the invalid-data custom relation charm."""
    return context_factory(InvalidDataCharm)


@pytest.fixture
def overwriting_context(context_factory) -> testing.Context:
    """Return a Context rooted at the overwriting custom relation charm."""
    return context_factory(OverwritingCharm)


@pytest.fixture
def side_effect_context(context_factory) -> testing.Context:
    """Return a Context rooted at the side-effect custom relation charm."""
    return context_factory(SideEffectCharm)


# pylint: disable=redefined-outer-name
def test_custom_relation_env_vars(envvar_context, tmp_path, container_name: str) -> None:
    """
    arrange: a charm with an env-var custom relation related with a valid ``uri``.
    act: reconcile on config-changed.
    assert: the workload environment exposes ``EXAMPLE_DB_URI`` and the unit is active.
    """
    base_state = _base_state(tmp_path)
    base_state["relations"].append(_example_db_relation("postgresql://user:pw@db:5432/app"))

    out = envvar_context.run(
        envvar_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["test"].environment
    assert environment["EXAMPLE_DB_URI"] == "postgresql://user:pw@db:5432/app"
    assert "example-db" in setup_calls


# pylint: disable=redefined-outer-name
def test_custom_relation_missing_required_blocks(envvar_context, tmp_path) -> None:
    """
    arrange: a charm with a required env-var custom relation that is not related.
    act: reconcile on config-changed.
    assert: the unit is blocked naming the missing custom relation.
    """
    envvar_context.charm_spec.meta["requires"]["example-db"]["optional"] = False
    base_state = _base_state(tmp_path)

    out = envvar_context.run(
        envvar_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.BlockedStatus("missing integrations: example-db")


# pylint: disable=redefined-outer-name
def test_custom_relation_required_but_not_ready_blocks(envvar_context, tmp_path) -> None:
    """
    arrange: a required custom relation is established but has not published usable data.
    act: reconcile on config-changed.
    assert: the unit is blocked naming the unready custom relation.
    """
    envvar_context.charm_spec.meta["requires"]["example-db"]["optional"] = False
    base_state = _base_state(tmp_path)
    base_state["relations"].append(_example_db_relation(None))

    out = envvar_context.run(
        envvar_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.BlockedStatus("missing integrations: example-db")


# pylint: disable=redefined-outer-name
def test_custom_relation_optional_absent_does_not_block(envvar_context, tmp_path) -> None:
    """
    arrange: a charm with an optional env-var custom relation that is not related.
    act: reconcile on config-changed.
    assert: the unit is active and no ``EXAMPLE_DB_URI`` is emitted.
    """
    base_state = _base_state(tmp_path)

    out = envvar_context.run(
        envvar_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(CONTAINER_NAME).plan.services["test"].environment
    assert "EXAMPLE_DB_URI" not in environment


# pylint: disable=redefined-outer-name
def test_custom_relation_invalid_data_blocks(invalid_context, tmp_path) -> None:
    """
    arrange: a charm with a custom relation related with malformed data (no ``uri``).
    act: reconcile on config-changed.
    assert: the unit is blocked naming the invalid custom relation.
    """
    base_state = _base_state(tmp_path)
    base_state["relations"].append(_invalid_db_relation({}))

    out = invalid_context.run(
        invalid_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.BlockedStatus("missing 'uri'")


# pylint: disable=redefined-outer-name
def test_custom_relation_context_is_injected(
    context_context, tmp_path, container_name: str
) -> None:
    """
    arrange: a charm with a custom relation that exposes the injected Context.
    act: reconcile on config-changed.
    assert: the workload environment contains the Context fields and setup ran.
    """
    base_state = _base_state(tmp_path)

    out = context_context.run(
        context_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["test"].environment
    assert environment["CTX_APP_NAME"] == "paas-test-k8s"
    assert environment["CTX_FRAMEWORK"] == "test"
    assert environment["CTX_PORT"] == "8080"
    assert environment["CTX_CONTAINER"] == CONTAINER_NAME
    assert "example-db" in setup_calls


# pylint: disable=redefined-outer-name
def test_side_effect_relation_reconciles_without_env(
    side_effect_context, tmp_path, container_name: str
) -> None:
    """
    arrange: a charm with a side-effect custom relation (no env vars).
    act: reconcile on config-changed.
    assert: the unit is active, no nginx env is emitted, and reconcile ran.
    """
    base_state = _base_state(tmp_path)

    out = side_effect_context.run(
        side_effect_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["test"].environment
    assert not {key for key in environment if key.startswith("NGINX")}
    assert "nginx-route" in reconcile_calls


# pylint: disable=redefined-outer-name
def test_custom_relation_relation_changed_triggers_restart(
    envvar_context, tmp_path, container_name: str
) -> None:
    """
    arrange: a charm with an env-var custom relation related with a valid ``uri``.
    act: emit relation-changed.
    assert: the observed event triggers a reconcile exposing ``EXAMPLE_DB_URI``.
    """
    base_state = _base_state(tmp_path)
    relation = _example_db_relation("postgresql://user:pw@db:5432/app")
    base_state["relations"].append(relation)

    out = envvar_context.run(
        envvar_context.on.relation_changed(relation, remote_unit=0),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["test"].environment
    assert environment["EXAMPLE_DB_URI"] == "postgresql://user:pw@db:5432/app"
