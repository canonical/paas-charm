# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""S3 lib wrapper unit tests."""
import pytest
from ops.testing import Harness

from paas_charm.rabbitmq import PaaSRabbitMQRelationData


@pytest.mark.parametrize(
    "unit_data, paas_app_data, rabbitmq_app_data, expected_relation_data",
    [
        pytest.param(
            {},
            {},
            {},
            None,
            id="empty relation data",
        ),
        pytest.param(
            {"hostname": "testinghostname"},
            {"hostname": "testinghostname"},
            {},
            None,
            id="empty password",
        ),
        pytest.param(
            {"password": "testingvalue"},
            {"password": "testingvalue"},
            {},
            None,
            id="empty hostname",
        ),
        pytest.param(
            {"password": "testingvalue", "hostname": "testinghostname"},
            {},
            {},
            PaaSRabbitMQRelationData(
                vhost="/",
                port=5672,
                hostname="testinghostname",
                username="flask-k8s",
                password="testingvalue",
                amqp_uri="amqp://flask-k8s:testingvalue@testinghostname:5672/",
            ),
            id="unit relation data",
        ),
        pytest.param(
            {},
            {"password": "testingvalue", "hostname": "testinghostname"},
            {},
            None,
            id="app relation data",
        ),
    ],
)
def test_rabbitmq_get_relation_data(
    flask_harness: Harness,
    unit_data: dict | None,
    rabbitmq_app_data: dict | None,
    paas_app_data: dict | None,
    expected_relation_data: PaaSRabbitMQRelationData | None,
):
    """
    arrange: given RabbitMQ relation data.
    act: when RabbitMQ get_relation_data is called.
    assert: expected relation data is returned.
    """
    flask_harness.begin()
    # Define some relations.
    rel_id = flask_harness.add_relation("rabbitmq", "rabbitmq")
    flask_harness.add_relation_unit(rel_id, "rabbitmq/0")
    flask_harness.update_relation_data(
        rel_id,
        "rabbitmq/0",
        unit_data,
    )
    flask_harness.update_relation_data(
        rel_id,
        "rabbitmq",
        rabbitmq_app_data,
    )
    flask_harness.update_relation_data(
        rel_id,
        flask_harness.charm.app.name,
        paas_app_data,
    )

    assert flask_harness.charm._rabbitmq.get_relation_data() == expected_relation_data
