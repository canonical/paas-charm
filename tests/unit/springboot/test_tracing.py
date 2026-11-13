# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Spring Boot charm tracing relation Scenario tests."""

from ops import testing


def test_tracing_relation(springboot_context, base_state) -> None:
    """
    arrange: relate the Spring Boot charm to a Tempo OTLP HTTP receiver.
    act: reconcile the tracing relation.
    assert: the workload exports traces over OTLP and keeps the metrics and logs exporters off.
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
    base_state["relations"].append(relation)

    out = springboot_context.run(
        springboot_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert environment["OTEL_TRACES_EXPORTER"] == "otlp"
    assert environment["OTEL_METRICS_EXPORTER"] == "none"
    assert environment["OTEL_LOGS_EXPORTER"] == "none"
    assert environment["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] == "http://test-ip:4318/v1/traces"
    assert environment["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] == "http/protobuf"
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in environment
    assert environment["OTEL_SERVICE_NAME"] == "spring-boot-k8s"


def test_tracing_not_activated(springboot_context, base_state) -> None:
    """
    arrange: prepare a Spring Boot unit without a tracing relation.
    act: reconcile the charm.
    assert: every OTEL exporter is disabled and no endpoint is exported.
    """
    out = springboot_context.run(
        springboot_context.on.config_changed(),
        testing.State(**base_state),
    )

    assert out.unit_status == testing.ActiveStatus()
    environment = out.get_container("app").plan.services["spring-boot"].environment
    assert environment["OTEL_TRACES_EXPORTER"] == "none"
    assert environment["OTEL_METRICS_EXPORTER"] == "none"
    assert environment["OTEL_LOGS_EXPORTER"] == "none"
    assert "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" not in environment
    assert "OTEL_SERVICE_NAME" not in environment
