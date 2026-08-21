# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scenario tests for Flask database migrations."""

import dataclasses
import pathlib

import pytest
from ops import pebble, testing

from paas_charm.database_migration import DatabaseMigrationStatus

from .constants import INTEGRATIONS_RELATION_DATA

MIGRATION_STATUS_PATH = pathlib.Path("tmp/flask/state/database-migration-status")


def _container_mount(base_state: dict) -> pathlib.Path:
    """Return the host path mounted at /flask in the workload container."""
    container = next(iter(base_state["containers"]))
    return pathlib.Path(container.mounts["flask"].source)


def _migration_exec(command: list[str], return_code: int = 0) -> testing.Exec:
    """Build a migration exec mock."""
    return testing.Exec(command, return_code=return_code)


def _container_with_exec(
    base_state: dict,
    migration_exec: testing.Exec,
    *,
    service_statuses: dict[str, pebble.ServiceStatus] | None = None,
) -> testing.Container:
    """Return the base container with focused migration and config-check exec mocks."""
    return dataclasses.replace(
        next(iter(base_state["containers"])),
        execs={
            testing.Exec(["/bin/python3"], return_code=0),
            testing.Exec(["python3", "-c", "import gevent"], return_code=0),
            migration_exec,
        },
        service_statuses=service_statuses or {"flask": pebble.ServiceStatus.INACTIVE},
    )


def _write_migration_file(base_state: dict, filename: str) -> pathlib.Path:
    """Create a migration file in the mounted Flask application directory."""
    app_dir = _container_mount(base_state) / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    migration_file = app_dir / filename
    migration_file.touch()
    return migration_file


def _status(out: testing.State, flask_context) -> str:
    """Read the persisted migration status from the Scenario container filesystem."""
    filesystem = out.get_container("app").get_filesystem(flask_context)
    return (filesystem / MIGRATION_STATUS_PATH).read_text()


def test_database_migration_retry_and_single_success(
    flask_context,
    base_state,
) -> None:
    """
    arrange: add migrate.sh and initially fail its exec.
    act: reconcile, retry on update-status, then reconcile twice more.
    assert: status transitions failed to completed and the successful script is not rerun.
    """
    command = ["bash", "-eo", "pipefail", "migrate.sh"]
    migration_file = _write_migration_file(base_state, "migrate.sh")
    failing_container = _container_with_exec(
        base_state,
        _migration_exec(command, return_code=1),
    )
    state = testing.State(**{**base_state, "containers": {failing_container}})

    out = flask_context.run(flask_context.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(
        f"database migration command {command} failed, will retry in next update-status"
    )
    assert _status(out, flask_context) == DatabaseMigrationStatus.FAILED

    successful_container = dataclasses.replace(
        out.get_container("app"),
        execs={
            testing.Exec(["/bin/python3"], return_code=0),
            _migration_exec(command),
        },
    )
    out = flask_context.run(
        flask_context.on.update_status(),
        dataclasses.replace(out, containers={successful_container}),
    )

    assert out.unit_status == testing.ActiveStatus()
    assert _status(out, flask_context) == DatabaseMigrationStatus.COMPLETED
    migration_history = [
        args for args in flask_context.exec_history["app"] if args.command == command
    ]
    assert len(migration_history) == 2
    assert migration_history[-1].working_dir == "/flask/app"
    assert migration_history[-1].user == migration_history[-1].group == "_daemon_"
    assert migration_history[-1].environment["FLASK_SECRET_KEY"] == "test"

    out = flask_context.run(flask_context.on.config_changed(), out)
    assert (
        len([args for args in flask_context.exec_history["app"] if args.command == command]) == 2
    )

    migration_file.unlink()
    (_container_mount(base_state) / "app" / "migrate.py").touch()
    flask_context.run(flask_context.on.config_changed(), out)
    assert (
        len([args for args in flask_context.exec_history["app"] if args.command == command]) == 2
    )


@pytest.mark.parametrize(
    "filename,command",
    [
        pytest.param("migrate", ["/flask/app/migrate"], id="executable"),
        pytest.param("migrate.sh", ["bash", "-eo", "pipefail", "migrate.sh"], id="shell"),
        pytest.param("migrate.py", ["python3", "migrate.py"], id="python"),
        pytest.param("manage.py", ["python3", "manage.py", "migrate"], id="django"),
    ],
)
def test_database_migrate_command(
    flask_context,
    base_state,
    filename: str,
    command: list[str],
) -> None:
    """
    arrange: add one supported migration file and its exec mock.
    act: reconcile the charm.
    assert: the exact command, environment, identity, directory, and status are recorded.
    """
    _write_migration_file(base_state, filename)
    container = _container_with_exec(base_state, _migration_exec(command))
    state = testing.State(**{**base_state, "containers": {container}})

    out = flask_context.run(flask_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    migration_history = [
        args for args in flask_context.exec_history["app"] if args.command == command
    ]
    assert len(migration_history) == 1
    exec_args = migration_history[0]
    assert exec_args.working_dir == "/flask/app"
    assert exec_args.user == exec_args.group == "_daemon_"
    assert exec_args.environment["FLASK_SECRET_KEY"] == "test"
    assert exec_args.environment["FLASK_BASE_URL"] == "http://flask-k8s.test-model:8000"
    assert _status(out, flask_context) == DatabaseMigrationStatus.COMPLETED


def test_migrations_run_second_time_optional_integration_integrated(
    flask_context,
    base_state,
) -> None:
    """
    arrange: run migrate.sh successfully without optional integrations.
    act: add a PostgreSQL relation and emit its relation-changed event.
    assert: migration reruns with the new database environment.
    """
    command = ["bash", "-eo", "pipefail", "migrate.sh"]
    _write_migration_file(base_state, "migrate.sh")
    container = _container_with_exec(base_state, _migration_exec(command))
    state = testing.State(**{**base_state, "containers": {container}})
    out = flask_context.run(flask_context.on.config_changed(), state)
    assert out.unit_status == testing.ActiveStatus()

    relation_data = INTEGRATIONS_RELATION_DATA["postgresql"]["app_data"]
    relation = testing.Relation(
        endpoint="postgresql",
        interface="postgresql_client",
        remote_app_data=relation_data,
        remote_units_data={0: {}},
    )
    out = flask_context.run(
        flask_context.on.relation_changed(relation, remote_unit=0),
        dataclasses.replace(out, relations={*out.relations, relation}),
    )

    assert out.unit_status == testing.ActiveStatus()
    migration_history = [
        args for args in flask_context.exec_history["app"] if args.command == command
    ]
    assert len(migration_history) == 2
    assert migration_history[0].environment.get("POSTGRESQL_DB_CONNECT_STRING") is None
    assert migration_history[1].environment["POSTGRESQL_DB_CONNECT_STRING"] == (
        "postgresql://test-username:test-password@test-postgresql:5432/test-database"
    )
    assert _status(out, flask_context) == DatabaseMigrationStatus.COMPLETED


def test_missing_required_integration_stops_all_and_sets_migration_to_pending(
    flask_context,
    base_state,
) -> None:
    """
    arrange: require S3, relate it, and complete migrate.sh with all services active.
    act: reconcile the state after removing S3.
    assert: every service stops and migration status returns to pending.
    """
    flask_context.charm_spec.meta["requires"]["s3"]["optional"] = False
    command = ["bash", "-eo", "pipefail", "migrate.sh"]
    _write_migration_file(base_state, "migrate.sh")
    relation = testing.Relation(
        endpoint="s3",
        interface="s3",
        remote_app_data=INTEGRATIONS_RELATION_DATA["s3"]["app_data"],
    )
    base_state["relations"].append(relation)
    container = _container_with_exec(base_state, _migration_exec(command))
    state = testing.State(**{**base_state, "containers": {container}})
    out = flask_context.run(flask_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    assert _status(out, flask_context) == DatabaseMigrationStatus.COMPLETED
    assert all(
        status == pebble.ServiceStatus.ACTIVE
        for status in out.get_container("app").service_statuses.values()
    )

    out = flask_context.run(
        flask_context.on.relation_broken(relation),
        out,
    )

    assert out.unit_status == testing.BlockedStatus("missing integrations: s3")
    assert all(
        status == pebble.ServiceStatus.INACTIVE
        for status in out.get_container("app").service_statuses.values()
    )
    assert _status(out, flask_context) == DatabaseMigrationStatus.PENDING
