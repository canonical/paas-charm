# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm database integration."""

import logging

import jubilant
import requests

from tests.integration.types import App

logger = logging.getLogger(__name__)


def test_db_migration(
    flask_db_app: App,
    juju: jubilant.Juju,
    http: requests.Session,
):
    """
    arrange: build and deploy the flask charm.
    act: deploy the database and relate it to the charm.
    assert: requesting the charm should return a correct response indicate
        the database migration script has been executed and only executed once.
    """
    # Deploy postgresql if not already present
    from tests.integration.conftest import deploy_postgresql

    deploy_postgresql(juju)

    juju.wait(lambda status: status.apps.get("postgresql-k8s") and status.apps["postgresql-k8s"].is_active)

    # Integrate with database
    try:
        juju.integrate(flask_db_app.name, "postgresql-k8s")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(
        lambda status: jubilant.all_active(status, flask_db_app.name, "postgresql-k8s"), timeout=20 * 60
    )

    status = juju.status()
    for unit in status.apps[flask_db_app.name].units.values():
        assert http.head(f"http://{unit.address}:8000/tables/users", timeout=5).status_code == 200
        user_creation_request = {"username": "foo", "password": "bar"}
        response = http.post(
            f"http://{unit.address}:8000/users", json=user_creation_request, timeout=5
        )
        assert response.status_code == 201
        response = http.post(
            f"http://{unit.address}:8000/users", json=user_creation_request, timeout=5
        )
        assert response.status_code == 400
