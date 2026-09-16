# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm tracing relation Scenario tests."""

from ops import testing


def test_tracing_relation(flask_context, base_state, container_name: str) -> None:
    """
    arrange: relate the Flask charm to a Tempo OTLP HTTP receiver.
    act: reconcile the tracing relation.
    assert: the workload receives the exact tracing endpoint and service name.
    """
    relation = testing.Relation(
        endpoint="tracing",
        interface="tracing",
        remote_app_data={
            "receivers": (
                '[{"protocol": {"name": "otlp_http", "type": "http"}, '
                '"url": "http://test-ip:4318"}]'
            )
        },
    )
    base_state["model"] = testing.Model(name="flask-model")
    base_state["relations"].append(relation)

    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["flask"].environment
    assert environment["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://test-ip:4318/"
    assert environment["OTEL_SERVICE_NAME"] == "flask-k8s"


def test_tracing_not_activated(flask_context, base_state, container_name: str) -> None:
    """
    arrange: prepare a Flask unit without a tracing relation.
    act: reconcile the charm.
    assert: the workload receives no tracing environment values.
    """
    base_state["model"] = testing.Model(name="flask-model")

    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container(container_name).plan.services["flask"].environment
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in environment
    assert "OTEL_SERVICE_NAME" not in environment
