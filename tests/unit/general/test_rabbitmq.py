# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""S3 lib wrapper unit tests."""

import pytest
from ops import testing

from examples.flask.charm.src.charm import FlaskCharm
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
                hostnames=["testinghostname"],
                amqp_uris=["amqp://flask-k8s:testingvalue@testinghostname:5672/%2F"],
            ),
            id="unit relation data",
        ),
        pytest.param(
            {},
            {},
            {"password": "testingvalue", "hostname": "testinghostname"},
            PaaSRabbitMQRelationData(
                vhost="/",
                port=5672,
                hostname="testinghostname",
                username="flask-k8s",
                password="testingvalue",
                amqp_uri="amqp://flask-k8s:testingvalue@testinghostname:5672/",
                hostnames=["testinghostname"],
                amqp_uris=["amqp://flask-k8s:testingvalue@testinghostname:5672/%2F"],
            ),
            id="app relation data",
        ),
    ],
)
def test_rabbitmq_get_relation_data(
    context_factory,
    flask_base_state: dict,
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
    relation = testing.Relation(
        endpoint="rabbitmq",
        interface="rabbitmq",
        local_app_data=paas_app_data,
        remote_app_data=rabbitmq_app_data,
        remote_units_data={0: unit_data},
    )
    flask_base_state["relations"].append(relation)
    context = context_factory(FlaskCharm)
    with context(
        context.on.relation_changed(relation), testing.State(**flask_base_state)
    ) as manager:
        assert manager.charm._rabbitmq.get_relation_data() == expected_relation_data
