# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm tracing relation unit tests."""

import unittest.mock

import ops
import pytest
from ops.testing import Harness

from .constants import DEFAULT_LAYER, FLASK_CONTAINER_NAME


def test_tracing_relation(harness: Harness):
    """
    arrange: Integrate the charm with the Tempo charm.
    act: Run all initial hooks.
    assert: The flask service should have the environment variable OTEL_EXPORTER_OTLP_ENDPOINT from
        the tracing relation. It should also have the environment variable OTEL_SERVICE_NAME set to "flask-k8s".
    """
    harness.set_model_name("flask-model")
    harness.add_relation(
        "tracing",
        "tempo-coordinator",
        app_data={
            "receivers": '[{"protocol": {"name": "otlp_http", "type": "http"}, "url": "http://test-ip:4318"}]'
        },
    )
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    assert service_env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "http://test-ip:4318"
    assert service_env["OTEL_SERVICE_NAME"] == "flask-k8s"


def test_tracing_not_activated(harness: Harness):
    """
    arrange: Deploy the flask charm without a relation to the Tempo charm.
    act: Run all initial hooks.
    assert: The flask service should not have the environment variables OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME.
    """
    harness.set_model_name("flask-model")

    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    assert service_env.get("OTEL_EXPORTER_OTLP_ENDPOINT", None) is None
    assert service_env.get("OTEL_SERVICE_NAME", None) is None
