# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""App unit tests."""

import pytest

from paas_charm.app import generate_db_env, generate_redis_env, generate_s3_env
from paas_charm.databases import DatabaseRelationData
from paas_charm.redis import PaaSRedisRelationData
from paas_charm.s3 import S3RelationData


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            S3RelationData.model_construct(
                access_key="access_key", secret_key="secret_key", bucket="bucket"
            ),
            {
                "S3_ACCESS_KEY": "access_key",
                "S3_SECRET_KEY": "secret_key",
                "S3_BUCKET": "bucket",
            },
            id="Minimum relation data",
        ),
        pytest.param(
            S3RelationData.model_construct(
                access_key="access_key",
                secret_key="secret_key",
                region="region",
                storage_class="standard",
                bucket="bucket",
                endpoint="endpoint",
                path="path",
                s3_api_version="version",
                s3_uri_style="url-style",
                tls_ca_chain=["---first---", "---second---"],
                attributes=["key1", "key2"],
            ),
            {
                "S3_ACCESS_KEY": "access_key",
                "S3_ADDRESSING_STYLE": "url-style",
                "S3_API_VERSION": "version",
                "S3_ATTRIBUTES": '["key1", "key2"]',
                "S3_BUCKET": "bucket",
                "S3_ENDPOINT": "endpoint",
                "S3_PATH": "path",
                "S3_REGION": "region",
                "S3_SECRET_KEY": "secret_key",
                "S3_STORAGE_CLASS": "standard",
                "S3_URI_STYLE": "url-style",
                "S3_TLS_CA_CHAIN": '["---first---", "---second---"]',
            },
            id="All relation data",
        ),
    ],
)
def test_s3_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given S3 relation data.
    act: when generate_s3_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_s3_env(relation_data) == expected_env


@pytest.mark.parametrize(
    "db_name, relation_data, expected_env",
    [
        pytest.param(
            "postgresql",
            DatabaseRelationData(
                uris="postgresql://test-username:test-password@test-postgresql:5432/test-database"
            ),
            {
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/test-database",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "test-database",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/test-database",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="PostgreSQL relation data",
        ),
        pytest.param(
            "mysql",
            DatabaseRelationData(
                uris="mysql://test-username:test-password@test-mysql:5432/test-database"
            ),
            {
                "MYSQL_DB_CONNECT_STRING": "mysql://test-username:test-password@test-mysql:5432/test-database",
                "MYSQL_DB_FRAGMENT": "",
                "MYSQL_DB_HOSTNAME": "test-mysql",
                "MYSQL_DB_NAME": "test-database",
                "MYSQL_DB_NETLOC": "test-username:test-password@test-mysql:5432",
                "MYSQL_DB_PARAMS": "",
                "MYSQL_DB_PASSWORD": "test-password",
                "MYSQL_DB_PATH": "/test-database",
                "MYSQL_DB_PORT": "5432",
                "MYSQL_DB_QUERY": "",
                "MYSQL_DB_SCHEME": "mysql",
                "MYSQL_DB_USERNAME": "test-username",
            },
            id="MySQL relation data",
        ),
        pytest.param(
            "mongo",
            DatabaseRelationData(
                uris="mongo://test-username:test-password@test-mongo:5432/test-database"
            ),
            {
                "MONGO_DB_CONNECT_STRING": "mongo://test-username:test-password@test-mongo:5432/test-database",
                "MONGO_DB_FRAGMENT": "",
                "MONGO_DB_HOSTNAME": "test-mongo",
                "MONGO_DB_NAME": "test-database",
                "MONGO_DB_NETLOC": "test-username:test-password@test-mongo:5432",
                "MONGO_DB_PARAMS": "",
                "MONGO_DB_PASSWORD": "test-password",
                "MONGO_DB_PATH": "/test-database",
                "MONGO_DB_PORT": "5432",
                "MONGO_DB_QUERY": "",
                "MONGO_DB_SCHEME": "mongo",
                "MONGO_DB_USERNAME": "test-username",
            },
            id="Mongo relation data",
        ),
    ],
)
def test_database_environ_mapper_generate_env(db_name, relation_data, expected_env):
    """
    arrange: given database relation data.
    act: when generate_db_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_db_env(db_name, relation_data) == expected_env


@pytest.mark.parametrize(
    "relation_data, expected_env",
    [
        pytest.param(None, {}, id="No relation data"),
        pytest.param(
            PaaSRedisRelationData.model_construct(url="redis://localhost"),
            {
                "REDIS_DB_CONNECT_STRING": "redis://localhost",
                "REDIS_DB_FRAGMENT": "",
                "REDIS_DB_HOSTNAME": "localhost",
                "REDIS_DB_NETLOC": "localhost",
                "REDIS_DB_PARAMS": "",
                "REDIS_DB_PATH": "",
                "REDIS_DB_QUERY": "",
                "REDIS_DB_SCHEME": "redis",
            },
            id="Minimum redis DSN",
        ),
        pytest.param(
            PaaSRedisRelationData.model_construct(url="redis://secret@localhost/1"),
            {
                "REDIS_DB_CONNECT_STRING": "redis://secret@localhost/1",
                "REDIS_DB_FRAGMENT": "",
                "REDIS_DB_HOSTNAME": "localhost",
                "REDIS_DB_NAME": "1",
                "REDIS_DB_NETLOC": "secret@localhost",
                "REDIS_DB_PARAMS": "",
                "REDIS_DB_PATH": "/1",
                "REDIS_DB_QUERY": "",
                "REDIS_DB_SCHEME": "redis",
                "REDIS_DB_USERNAME": "secret",
            },
            id="Max redis DSN",
        ),
        pytest.param(
            PaaSRedisRelationData.model_construct(url="http://redisuri"),
            {
                "REDIS_DB_CONNECT_STRING": "http://redisuri",
                "REDIS_DB_FRAGMENT": "",
                "REDIS_DB_HOSTNAME": "redisuri",
                "REDIS_DB_NETLOC": "redisuri",
                "REDIS_DB_PARAMS": "",
                "REDIS_DB_PATH": "",
                "REDIS_DB_QUERY": "",
                "REDIS_DB_SCHEME": "http",
            },
            id="http redis DSN",
        ),
    ],
)
def test_redis_environ_mapper_generate_env(relation_data, expected_env):
    """
    arrange: given Redis relation data.
    act: when generate_env method is called.
    assert: expected environment variables are generated.
    """
    assert generate_redis_env(relation_data) == expected_env
