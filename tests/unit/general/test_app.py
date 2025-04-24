# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""App unit tests."""
import pytest

from paas_charm.app import generate_redis_env
from paas_charm.redis import PaaSRedisRelationData


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
