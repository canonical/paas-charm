# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Valkey charm integration unit tests."""

import pytest

from paas_charm.valkey import InvalidValkeyRelationDataError, PaaSValkeyRelationData


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
            {"hostname": "valkey.url", "port": "8888"},
            {},
            PaaSValkeyRelationData(url="valkey://valkey.url:8888"),
            id="minimum url data",
        ),
        pytest.param(
            {"hostname": "user:pass@valkey.url", "port": "8888"},
            {},
            PaaSValkeyRelationData(url="valkey://user:pass@valkey.url:8888"),
            id="all url data",
        ),
        pytest.param(
            {"hostname": "user:pass@valkey.url", "port": "8888"},
            {"leader-host": "leader:host@valkey.url"},
            PaaSValkeyRelationData(url="valkey://leader:host@valkey.url:8888"),
            id="all url data with leader host",
        ),
    ],
)
def test_paas_valkey_requirer_to_relation_data(
    flask_harness, unit_relation_data, app_relation_data, expected_relation_data
):
    """
    arrange: given valkey relation.
    act: when to_relation_data is called.
    assert: expected relation data is returned.
    """
    flask_harness.begin()
    # Define some relations.
    rel_id = flask_harness.add_relation("valkey", "valkey")
    flask_harness.add_relation_unit(rel_id, "valkey/0")
    flask_harness.update_relation_data(
        rel_id,
        "valkey/0",
        unit_relation_data,
    )
    flask_harness.update_relation_data(
        rel_id,
        "valkey",
        app_relation_data,
    )

    assert flask_harness.charm._valkey.to_relation_data() == expected_relation_data


def test_paas_valkey_url():
    """
    arrange: given valkey relation data.
    act: when url is stringified.
    assert: expected URL string is returned.
    """
    relation_data = PaaSValkeyRelationData(url="valkey://user:password@valkey.url")

    assert str(relation_data.url) == "valkey://user:password@valkey.url"


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
                "hostname": "overridden.url",
            },
            {"leader-host": "invalid:url:segments@noturl"},
            id="invalid leader-hostname",
        ),
    ],
)
def test_valkey_url_invalid(flask_harness, unit_relation_data, app_relation_data):
    """
    arrange: given invalid valkey relation data.
    act: when to_relation_data is called.
    assert: InvalidValkeyRelationDataError is raised.
    """
    # Define some relations.
    rel_id = flask_harness.add_relation("valkey", "valkey")
    flask_harness.add_relation_unit(rel_id, "valkey/0")
    flask_harness.update_relation_data(
        rel_id,
        "valkey/0",
        unit_relation_data,
    )
    flask_harness.update_relation_data(
        rel_id,
        "valkey",
        app_relation_data,
    )
    flask_harness.begin()

    with pytest.raises(InvalidValkeyRelationDataError) as exc:
        print(flask_harness.charm._valkey.to_relation_data())

    assert "Invalid PaaSValkeyRelationData" in str(exc.value)
