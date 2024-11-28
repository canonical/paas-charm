# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm database relations unit tests."""

import unittest.mock

import pytest

from paas_charm.databases import get_uri

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


@pytest.mark.parametrize("relation, expected_output", DATABASE_GET_URI_TEST_PARAMS)
def test_database_get_uri_mocked(
    relation: tuple,
    expected_output: dict,
) -> None:
    """
    arrange: mock relation database
    act: run get_uri over the mocked database requires
    assert: get_uri() should return the correct database uri
    """
    # Create the databases mock with the relation data
    interface = relation["interface"]
    database_require = unittest.mock.MagicMock()
    database_require.relation_name = interface
    database_require.fetch_relation_data = unittest.mock.MagicMock(
        return_value={"data": relation["data"]}
    )
    database_require.database = relation["data"].get("database", "flask-app")
    assert get_uri(database_require) == expected_output
