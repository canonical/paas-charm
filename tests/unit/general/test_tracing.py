# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tempo lib wrapper unit tests."""

from unittest.mock import MagicMock

import pytest
from ops import testing

from paas_charm.charm import PaasCharm
from paas_charm.exceptions import InvalidRelationInterfaceError
from paas_charm.tracing import (
    InvalidTracingRelationDataError,
    PaaSTracingRelationData,
    ProtocolNotRequestedError,
    TracingRelation,
)


def _get_tracing_relation(charm: PaasCharm) -> TracingRelation:
    """Return the built-in TracingRelation instance from a charm."""
    return next(
        relation for relation in charm._custom_relations if isinstance(relation, TracingRelation)
    )


@pytest.mark.parametrize(
    "is_ready, endpoint, expected",
    [
        pytest.param(False, None, None, id="Not ready"),
        pytest.param(True, "", None, id="No endpoint data"),
        pytest.param(
            True,
            "http://test-endpoint.test",
            PaaSTracingRelationData(
                endpoint="http://test-endpoint.test", service_name="paas-test-k8s"
            ),
            id="Valid endpoint data",
        ),
    ],
)
def test_requirer_to_relation_data(
    monkeypatch, generic_context, generic_state, is_ready, endpoint, expected
):
    """
    arrange: given tracing relation data.
    act: when to_relation_data is called.
    assert: expected relation data is returned.
    """
    with generic_context(generic_context.on.start(), testing.State(**generic_state)) as manager:
        charm: PaasCharm = manager.charm
        tracing_requirer = _get_tracing_relation(charm)._requirer
        monkeypatch.setattr(tracing_requirer, "is_ready", MagicMock(return_value=is_ready))
        monkeypatch.setattr(tracing_requirer, "get_endpoint", MagicMock(return_value=endpoint))
        assert tracing_requirer.to_relation_data() == expected


def test_requirer_to_relation_data_protocol_not_request_error(generic_context, generic_state):
    """
    arrange: given a monkeypatched get_endpoint method that raises ProtocolNotRequestedError.
    act: when to_relation_data is called.
    assert: InvalidTracingRelationDataError is raised.
    """
    with generic_context(generic_context.on.start(), testing.State(**generic_state)) as manager:
        charm: PaasCharm = manager.charm
        tracing_requirer = _get_tracing_relation(charm)._requirer
        tracing_requirer.is_ready = MagicMock(return_value=True)
        tracing_requirer.get_endpoint = MagicMock(side_effect=ProtocolNotRequestedError)
        with pytest.raises(InvalidTracingRelationDataError) as exc:
            tracing_requirer.to_relation_data()

    assert "Invalid PaaSTracingRelationData" in str(exc)


@pytest.mark.parametrize(
    "endpoint",
    [
        pytest.param("not_a_url", id="invalid URL"),
        pytest.param("http://invalid:port", id="invalid port"),
    ],
)
def test_requirer_to_validation_error(monkeypatch, generic_context, generic_state, endpoint):
    """
    arrange: given incomplete/invalid relation data.
    act: when to_relation_data is called.
    assert: InvalidTracingRelationDataError is raised.
    """
    with generic_context(generic_context.on.start(), testing.State(**generic_state)) as manager:
        charm: PaasCharm = manager.charm
        tracing_requirer = _get_tracing_relation(charm)._requirer
        monkeypatch.setattr(tracing_requirer, "is_ready", MagicMock(return_value=True))
        monkeypatch.setattr(tracing_requirer, "get_endpoint", MagicMock(return_value=endpoint))
        with pytest.raises(InvalidTracingRelationDataError) as exc:
            tracing_requirer.to_relation_data()

    assert "invalid options" in str(exc.value)


def test_tracing_setup_invalid_relation_interface():
    """
    arrange: given a tracing relation configured with an invalid interface.
    act: when the relation is set up.
    assert: InvalidRelationInterfaceError is raised.
    """
    mock_charm = MagicMock()
    mock_charm.framework.meta.requires["tracing"].interface_name = "invalid"
    relation = TracingRelation.__new__(TracingRelation)
    relation._charm = mock_charm

    with pytest.raises(
        InvalidRelationInterfaceError,
        match="Built-in tracing relation interface is not 'tracing'",
    ):
        relation.setup(MagicMock())
