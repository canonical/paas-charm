# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm smtp relation unit tests."""

import unittest.mock

import ops
import pytest
from ops.testing import Harness

from .constants import DEFAULT_LAYER, FLASK_CONTAINER_NAME

SMTP_DATA = {
    "auth_type": "none",
    "domain": "example.com",
    "host": "test-ip",
    "port": "1025",
    "skip_ssl_verify": "False",
    "transport_security": "none",
}


def test_smtp_relation(harness: Harness, request: pytest.FixtureRequest):
    """
    arrange: Integrate the charm with the smtp-integrator charm.
    act: Run all initial hooks.
    assert: The flask service should have the environment variables related to smtp.
    """
    harness.set_model_name("flask-model")
    harness.add_relation(
        "smtp",
        "smtp-integrator",
        app_data=SMTP_DATA,
    )
    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    assert service_env.get("SMTP_AUTH_TYPE") is None
    assert service_env["SMTP_DOMAIN"] == SMTP_DATA["domain"]
    assert service_env["SMTP_HOST"] == SMTP_DATA["host"]
    assert service_env["SMTP_PORT"] == SMTP_DATA["port"]
    assert service_env["SMTP_SKIP_SSL_VERIFY"] == SMTP_DATA["skip_ssl_verify"]
    assert service_env.get("SMTP_TRANSPORT_SECURITY") is None


def test_smtp_not_activated(harness: Harness):
    """
    arrange: Deploy the charm without a relation to the smtp-integrator charm.
    act: Run all initial hooks.
    assert: The flask service should not have the environment variables related to smtp.
    """
    harness.set_model_name("flask-model")

    container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    container.add_layer("a_layer", DEFAULT_LAYER)

    harness.begin_with_initial_hooks()

    assert harness.model.unit.status == ops.ActiveStatus()
    service_env = container.get_plan().services["flask"].environment
    assert service_env.get("SMTP_AUTH_TYPE") is None
    assert service_env.get("SMTP_DOMAIN") is None
    assert service_env.get("SMTP_HOST") is None
    assert service_env.get("SMTP_PORT") is None
    assert service_env.get("SMTP_SKIP_SSL_VERIFY") is None
    assert service_env.get("SMTP_TRANSPORT_SECURITY") is None
