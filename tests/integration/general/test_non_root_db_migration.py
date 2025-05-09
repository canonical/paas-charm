#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for non-root Charms db migration."""

import logging

import juju.model
import pytest
import requests
from juju.application import Application

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
    arrange: build and deploy the non-root charm.
    act: deploy the database and relate it to the charm.
    assert: requesting the charm should return a correct response indicate
        the database migration script has been executed and only executed once.
    """
    request.getfixturevalue(non_root_app_fixture)
    await model.wait_for_idle(
        apps=[app_name, postgresql_k8s.name],
        status="active",
        timeout=20 * 60,
        idle_period=2 * 60,
    )
    for unit_ip in await get_unit_ips(app_name):
        if app_name == "fastapi-k8s":
            assert (
                requests.get(f"http://{unit_ip}:{port}/{endpoint}", timeout=5).status_code == 200
            )
        else:
            assert (
                requests.head(f"http://{unit_ip}:{port}/{endpoint}", timeout=5).status_code == 200
            )
