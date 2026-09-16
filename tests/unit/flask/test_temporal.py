# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask custom Temporal relation Scenario tests."""

from ops import testing


def _temporal_relation(data: dict[str, str]) -> testing.Relation:
    """Build a temporal-host-info relation with remote application data."""
    return testing.Relation(
        endpoint="temporal-host-info",
        interface="temporal-host-info",
        remote_app_data=data,
    )


def test_temporal_relation_environment(flask_context, base_state, container_name: str) -> None:
    """
    arrange: relate Flask to a Temporal server publishing valid host information.
    act: reconcile the relation-changed event.
    assert: the workload receives the Temporal host and port environment variables.
    """
    relation = _temporal_relation({"host": "temporal.local.test", "port": "7233"})
    base_state["relations"].append(relation)

    out = flask_context.run(
        flask_context.on.relation_changed(relation),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["flask"].environment
    assert environment["TEMPORAL_HOST"] == "temporal.local.test"
    assert environment["TEMPORAL_PORT"] == "7233"


def test_temporal_relation_invalid_data_blocks(flask_context, base_state) -> None:
    """
    arrange: relate Flask to a Temporal server publishing an invalid port.
    act: reconcile a config-changed event.
    assert: the workload is blocked with the Temporal data validation error.
    """
    relation = _temporal_relation({"host": "temporal.local.test", "port": "invalid"})
    base_state["relations"].append(relation)

    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.BlockedStatus("invalid Temporal port")


def test_temporal_relation_is_optional(flask_context, base_state, container_name: str) -> None:
    """
    arrange: prepare the Flask charm without a Temporal relation.
    act: reconcile a config-changed event.
    assert: Flask remains active without Temporal environment variables.
    """
    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["flask"].environment
    assert "TEMPORAL_HOST" not in environment
    assert "TEMPORAL_PORT" not in environment
