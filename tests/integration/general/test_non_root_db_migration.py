#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask charm COS integration."""

import logging

import juju.client.client
import juju.model
import pytest
import requests
from juju.application import Application
from juju.errors import JujuError

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "non_root_app_fixture, app_name, endpoint, port",
    [
        pytest.param(
            "flask_non_root_db_app",
            "flask-k8s",
            "tables/users",
            8000,
            id="Flask non-root",
        ),
        pytest.param("django_non_root_app", "django-k8s", "len/users", 8000, id="Django non-root"),
        pytest.param(
            "fastapi_non_root_app",
            "fastapi-k8s",
            "table/users",
            8080,
            id="FastAPI non-root",
        ),
        pytest.param(
            "go_non_root_app",
            "go-k8s",
            "postgresql/migratestatus",
            8080,
            id="Go non-root",
        ),
    ],
)
@pytest.mark.skip_juju_version("3.6")  # Only Juju>=3.6 supports non-root users
async def test_non_root_db_migration(
    non_root_app_fixture: str,
    app_name: str,
    endpoint: str,
    port: int,
    model: juju.model.Model,
    get_unit_ips,
    postgresql_k8s: Application,
    request,
):
    """
    arrange: build and deploy the flask charm.
    act: deploy the database and relate it to the charm.
    assert: requesting the charm should return a correct response indicate
        the database migration script has been executed and only executed once.
    """
    try:
        request.getfixturevalue(non_root_app_fixture)
    except JujuError as e:
        if "application already exists" in str(e):
            logger.info(f"smtp-integrator is already deployed {e}")
        else:
            raise e
    await model.wait_for_idle(
        apps=[app_name, postgresql_k8s.name], status="active", timeout=20 * 60, idle_period=5 * 60
    )
    for unit_ip in await get_unit_ips(app_name):
        if non_root_app_fixture == "fastapi_non_root_app":
            assert requests.get(f"http://{unit_ip}:{port}/{endpoint}", timeout=5).status_code == 200
        else:
            assert requests.head(f"http://{unit_ip}:{port}/{endpoint}", timeout=5).status_code == 200

