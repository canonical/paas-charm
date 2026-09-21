# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm database relations unit tests."""

from unittest.mock import MagicMock

import pytest

from paas_charm.charm import PaasCharm
from paas_charm.databases import PaaSDatabaseRelationData, PaaSDatabaseRequires

DATABASE_GET_URI_TEST_PARAMS = [
    (
        {
            "interface": "mysql",
            "data": {
                "endpoints": "test-mysql:3306",
                "password": "test-password",
                "username": "test-username",
            },
        },
        "mysql://test-username:test-password@test-mysql:3306/flask-app",
    ),
    (
        {
            "interface": "postgresql",
            "data": {
                "database": "test-database",
                "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
                "password": "test-password",
                "username": "test-username",
            },
        },
        "postgresql://test-username:test-password@test-postgresql:5432/test-database",
    ),
    (
        {
            "interface": "mongodb",
            "data": {"uris": "mongodb://foobar/"},
        },
        "mongodb://foobar/",
    ),
]


@pytest.mark.parametrize(
    "database, relation_data, expected",
    [
        pytest.param("postgresql", {}, None, id="No relation data"),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "password": "test-password",
                    "endpoints": "test-endpoint",
                }
            },
            None,
            id="Missing username data",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "username": "test-user",
                    "endpoints": "test-endpoint",
                }
            },
            None,
            id="Missing password data",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                }
            },
            None,
            id="Missing endpoint data",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "uris": "test-uri",
                }
            },
            PaaSDatabaseRelationData(uris="test-uri"),
            id="Relation data with uris",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                    "database": "test-database",
                    "endpoints": "test-endpoint",
                }
            },
            PaaSDatabaseRelationData(
                uris="postgresql://test-user:test-password@test-endpoint/test-database"
            ),
            id="Relation data with non-uri fields",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                    "endpoints": "test-endpoint",
                }
            },
            PaaSDatabaseRelationData(
                uris="postgresql://test-user:test-password@test-endpoint/flask-k8s"
            ),
            id="Relation data with non-uri fields with default database name",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                    "endpoints": "test-endpoint-0,test-endpoint-1",
                }
            },
            PaaSDatabaseRelationData(
                uris="postgresql://test-user:test-password@test-endpoint-0/flask-k8s"
            ),
            id="Relation data with non-uri fields with multiple endpoints",
        ),
        pytest.param(
            "mysql",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                    "endpoints": "test-endpoint-0,test-endpoint-1",
                }
            },
            PaaSDatabaseRelationData(
                uris="mysql://test-user:test-password@test-endpoint-0/flask-k8s"
            ),
            id="mysql",
        ),
        pytest.param(
            "mongodb",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                    "endpoints": "test-endpoint-0,test-endpoint-1",
                }
            },
            PaaSDatabaseRelationData(
                uris="mongodb://test-user:test-password@test-endpoint-0/flask-k8s"
            ),
            id="mongodb",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "uris": (
                        "postgresql://" "test-user:test-password" "@test-endpoint/test-database"
                    ),
                    "tls": "False",
                }
            },
            PaaSDatabaseRelationData(
                uris=(
                    "postgresql://"
                    "test-user:test-password"
                    "@test-endpoint/test-database?sslmode=disable"
                )
            ),
            id="PostgreSQL URI with TLS disabled",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "uris": (
                        "postgresql://"
                        "test-user:test-password"
                        "@test-endpoint/test-database?connect_timeout=10"
                    ),
                    "tls": "True",
                }
            },
            PaaSDatabaseRelationData(
                uris=(
                    "postgresql://"
                    "test-user:test-password"
                    "@test-endpoint/test-database?connect_timeout=10&sslmode=require"
                )
            ),
            id="PostgreSQL URI with TLS enabled and existing query",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "uris": (
                        "postgresql://"
                        "test-user:test-password"
                        "@test-endpoint/test-database?sslmode=verify-full"
                    ),
                    "tls": "True",
                }
            },
            PaaSDatabaseRelationData(
                uris=(
                    "postgresql://"
                    "test-user:test-password"
                    "@test-endpoint/test-database?sslmode=verify-full"
                )
            ),
            id="PostgreSQL URI with explicit SSL mode",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                    "database": "test-database",
                    "endpoints": "test-endpoint",
                    "tls": "false",
                }
            },
            PaaSDatabaseRelationData(
                uris=(
                    "postgresql://"
                    "test-user:test-password"
                    "@test-endpoint/test-database?sslmode=disable"
                )
            ),
            id="PostgreSQL non-URI fields with TLS disabled",
        ),
        pytest.param(
            "postgresql",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                    "database": "test-database",
                    "endpoints": "test-endpoint",
                    "tls": "true",
                }
            },
            PaaSDatabaseRelationData(
                uris=(
                    "postgresql://"
                    "test-user:test-password"
                    "@test-endpoint/test-database?sslmode=require"
                )
            ),
            id="PostgreSQL non-URI fields with TLS enabled",
        ),
        pytest.param(
            "mysql",
            {
                "0": {
                    "username": "test-user",
                    "password": "test-password",
                    "database": "test-database",
                    "endpoints": "test-endpoint",
                    "tls": "False",
                }
            },
            PaaSDatabaseRelationData(
                uris="mysql://" "test-user:test-password" "@test-endpoint/test-database"
            ),
            id="MySQL ignores TLS field",
        ),
    ],
)
def test_paas_database_requires_to_relation_data(
    monkeypatch, harness, database, relation_data, expected
):
    """
    arrange: given relation data.
    act: when PaaSDatabaseRequires.to_relation_data() is called.
    assert: expected DatabaseRelationData is returned.
    """
    harness.begin()
    charm: PaasCharm = harness.charm
    db_requires: PaaSDatabaseRequires = charm._database_requirers[database]
    monkeypatch.setattr(db_requires, "fetch_relation_data", MagicMock(return_value=relation_data))
    assert db_requires.to_relation_data() == expected
