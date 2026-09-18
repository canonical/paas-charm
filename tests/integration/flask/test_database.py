#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm database integration."""

import logging
import time

import jubilant
import pytest
import requests

from tests.integration.types import App

# caused by pytest fixtures
# pylint: disable=too-many-arguments

logger = logging.getLogger(__name__)

POSTGRESQL_APP = "postgresql-k8s"
POSTGRESQL_STATUS_ENDPOINT = "postgresql/status"
TLS_CERTIFICATES_APP = "postgresql-test-certificates"
WORKLOAD_PEBBLE_SOCKET = "/charm/containers/flask-app/pebble.socket"


def _wait_for_postgresql_sslmode(
    juju: jubilant.Juju,
    app: App,
    expected_sslmode: str,
    timeout: int = 300,
) -> None:
    """Wait for the PostgreSQL connection string to contain the expected SSL mode.

    Args:
        juju: Jubilant Juju wrapper.
        app: Deployed application.
        expected_sslmode: Expected PostgreSQL sslmode value.
        timeout: Maximum number of seconds to wait.

    Raises:
        AssertionError: If the expected SSL mode is not applied before the timeout.
    """
    unit_name = next(iter(juju.status().apps[app.name].units))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = juju.exec(
            command=(
                f"PEBBLE_SOCKET={WORKLOAD_PEBBLE_SOCKET} pebble plan "
                "| grep -o 'sslmode=[a-z-]*'"
            ),
            unit=unit_name,
        )
        if task.return_code == 0 and f"sslmode={expected_sslmode}" in task.stdout:
            return
        time.sleep(10)

    raise AssertionError(f"PostgreSQL sslmode={expected_sslmode} was not applied")


def _assert_postgresql_connection(
    juju: jubilant.Juju,
    app: App,
    session: requests.Session,
) -> None:
    """Assert that the application can connect to PostgreSQL.

    Args:
        juju: Jubilant Juju wrapper.
        app: Deployed application.
        session: HTTP session with retry behavior.
    """
    unit = next(iter(juju.status().apps[app.name].units.values()))
    response = session.get(
        f"http://{unit.address}:8000/{POSTGRESQL_STATUS_ENDPOINT}",
        timeout=5,
    )
    assert response.status_code == 200
    assert response.text == "SUCCESS"


@pytest.mark.parametrize(
    "endpoint, db_name, db_channel, revision, trust",
    [
        ("postgresql/status", "postgresql-k8s", "14/edge", None, True),
    ],
)
def test_with_database(
    juju: jubilant.Juju,
    flask_app: App,
    session_with_retry: requests.Session,
    endpoint: str,
    db_name: str,
    db_channel: str,
    revision: int | None,
    trust: bool,
):
    """
    arrange: build and deploy the flask charm.
    act: deploy the database and relate it to the charm.
    assert: requesting the charm should return a correct response
    """
    # Deploy database if not already deployed
    if not juju.status().apps.get(db_name):
        juju.deploy(db_name, channel=db_channel, revision=revision, trust=trust)

    juju.wait(lambda status: status.apps.get(db_name, False) and status.apps[db_name].is_active)

    # Integrate with database
    try:
        juju.integrate(flask_app.name, f"{db_name}:database")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: jubilant.all_active(status, flask_app.name, db_name))

    status = juju.status()
    for unit in status.apps[flask_app.name].units.values():
        # Retry up to 10 times with 60 second delay
        for _ in range(10):
            response = session_with_retry.get(f"http://{unit.address}:8000/{endpoint}", timeout=5)
            if "SUCCESS" == response.text:
                return
            time.sleep(60)
        assert response.status_code == 200
        assert "SUCCESS" == response.text


def test_postgresql_connection_string_respects_tls(
    juju: jubilant.Juju,
    flask_app: App,
    session_with_retry: requests.Session,
):
    """
    arrange: Deploy Flask integrated with PostgreSQL without TLS.
    assert: The connection string disables SSL and the application connects.
    act: Enable PostgreSQL TLS using self-signed certificates.
    assert: The connection string requires SSL and the application connects.
    act: Disable PostgreSQL TLS.
    assert: The connection string disables SSL and the application connects.
    """
    _wait_for_postgresql_sslmode(juju, flask_app, "disable")
    _assert_postgresql_connection(juju, flask_app, session_with_retry)

    if not juju.status().apps.get(TLS_CERTIFICATES_APP):
        juju.deploy(
            "self-signed-certificates",
            app=TLS_CERTIFICATES_APP,
            channel="1/stable",
        )
    juju.wait(lambda status: status.apps[TLS_CERTIFICATES_APP].is_active)

    juju.integrate(
        f"{TLS_CERTIFICATES_APP}:certificates",
        f"{POSTGRESQL_APP}:certificates",
    )
    try:
        _wait_for_postgresql_sslmode(juju, flask_app, "require")
        juju.wait(
            lambda status: jubilant.all_active(
                status,
                flask_app.name,
                POSTGRESQL_APP,
                TLS_CERTIFICATES_APP,
            )
        )
        _assert_postgresql_connection(juju, flask_app, session_with_retry)
    finally:
        juju.remove_relation(
            f"{TLS_CERTIFICATES_APP}:certificates",
            f"{POSTGRESQL_APP}:certificates",
        )

    _wait_for_postgresql_sslmode(juju, flask_app, "disable")
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            flask_app.name,
            POSTGRESQL_APP,
        )
    )
    _assert_postgresql_connection(juju, flask_app, session_with_retry)
