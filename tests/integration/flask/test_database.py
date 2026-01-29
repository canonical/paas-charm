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


@pytest.mark.parametrize(
    "endpoint, db_name, db_channel, revision, trust",
    [
        ("postgresql/status", "postgresql-k8s", "14/edge", None, True),
    ],
)
def test_with_database(
    juju: jubilant.Juju,
    flask_app: App,
    http: requests.Session,
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
            response = http.get(f"http://{unit.address}:8000/{endpoint}", timeout=5)
            if "SUCCESS" == response.text:
                return
            time.sleep(60)
        assert response.status_code == 200
        assert "SUCCESS" == response.text
