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
    "endpoint,db_name, db_channel, revision, trust",
    [
        ("postgresql/status", "postgresql-k8s", "14/edge", None, True),
    ],
)
def test_with_database(
    juju: jubilant.Juju,
    flask_app_with_configs: App,
    endpoint: str,
    db_name: str,
    db_channel: str,
    revision: str | None,
    trust: bool,
):
    """
    arrange: build and deploy the flask charm.
    act: deploy the database and relate it to the charm.
    assert: requesting the charm should return a correct response
    """
    # Deploy database if not already deployed
    if not juju.status().apps.get(db_name):
        deploy_args = [db_name, "--channel", db_channel]
        if revision:
            deploy_args.extend(["--revision", revision])
        if trust:
            deploy_args.append("--trust")
        juju.cli("deploy", *deploy_args)

    juju.wait(lambda status: status.apps[db_name].is_active, error=jubilant.any_blocked)

    # Add relation
    try:
        juju.integrate(flask_app_with_configs.name, f"{db_name}:database")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: jubilant.all_active(status, flask_app_with_configs.name, db_name))

    # Test database connectivity
    status = juju.status()
    for unit in status.apps[flask_app_with_configs.name].units.values():
        for _ in range(10):
            response = requests.get(f"http://{unit.address}:8000/{endpoint}", timeout=5)
            if "SUCCESS" == response.text:
                return
            time.sleep(60)
        assert response.status_code == 200
        assert "SUCCESS" == response.text
