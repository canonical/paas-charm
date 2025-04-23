# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Redis charm integration unit tests."""

import pytest

from paas_charm.charm_state import PaaSRedisRelationData
from paas_charm.redis import InvalidRedisRelationDataError


@pytest.mark.parametrize(
    "unit_relation_data, app_relation_data, expected_relation_data",
    [
        pytest.param(
            {},
            {},
            None,
            id="none relation data",
        ),
        pytest.param(
            {"hostname": "redis.url", "port": "8888"},
            {},
            PaaSRedisRelationData(url="redis://redis.url:8888"),
            id="minimum url data",
        ),
        pytest.param(
            {"hostname": "user:pass@redis.url", "port": "8888"},
            {},
            PaaSRedisRelationData(url="redis://user:pass@redis.url:8888"),
            id="all url data",
        ),
        pytest.param(
            {"hostname": "user:pass@redis.url", "port": "8888"},
            {"leader-host": "leader:host@redis.url"},
            PaaSRedisRelationData(url="redis://leader:host@redis.url:8888"),
            id="all url data with leader host",
        ),
    ],
)
def test_paas_redis_requirer_to_relation_data(
    flask_harness, unit_relation_data, app_relation_data, expected_relation_data
):
    """Test PaaSRedisRequires to relation data conversion."""
    flask_harness.begin()
    # Define some relations.
    rel_id = flask_harness.add_relation("redis", "redis")
    flask_harness.add_relation_unit(rel_id, "redis/0")
    flask_harness.update_relation_data(
        rel_id,
        "redis/0",
        unit_relation_data,
    )
    flask_harness.update_relation_data(
        rel_id,
        "redis",
        app_relation_data,
    )

    assert flask_harness.charm._redis.to_relation_data() == expected_relation_data


def test_paas_redis_url():
    """Test PaaSSAMLRelationData properties.

    This test checks that the default path is not added to the URL, i.e. the /0
    is omitted from redis://user:password@redis.url:6379/0
    """
    relation_data = PaaSRedisRelationData(url="redis://user:password@redis.url")

    assert str(relation_data.url) == "redis://user:password@redis.url:6379"


@pytest.mark.parametrize(
    "unit_relation_data, app_relation_data",
    [
        pytest.param(
            {"hostname": "", "port": "notanumber"},
            {},
            id="invalid port",
        ),
        pytest.param(
            {
                "hostname": "invalid:url:segments@noturl",
            },
            {},
            id="invalid hostname",
        ),
        pytest.param(
            {
                "hostname": "overriden.url",
            },
            {"leader-host": "invalid:url:segments@noturl"},
            id="invalid leader-hostname",
        ),
    ],
)
def test_redis_url_invalid(flask_harness, unit_relation_data, app_relation_data):
    """Test invalid relation data error."""
    # Define some relations.
    rel_id = flask_harness.add_relation("redis", "redis")
    flask_harness.add_relation_unit(rel_id, "redis/0")
    flask_harness.update_relation_data(
        rel_id,
        "redis/0",
        unit_relation_data,
    )
    flask_harness.update_relation_data(
        rel_id,
        "redis",
        app_relation_data,
    )
    flask_harness.begin()

    with pytest.raises(InvalidRedisRelationDataError) as exc:
        print(flask_harness.charm._redis.to_relation_data())

    assert "Invalid PaaSRedisRelationData" in str(exc.value)
