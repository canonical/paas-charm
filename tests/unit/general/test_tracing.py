# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tempo lib wrapper unit tests."""

from unittest.mock import MagicMock

import pytest

from paas_charm.charm import PaasCharm
from paas_charm.tracing import (
    InvalidTracingRelationDataError,
    PaaSTracingRelationData,
    ProtocolNotRequestedError,
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
            id="No endpoint data",
        ),
    ],
)
def test_requirer_to_relation_data(monkeypatch, generic_harness, is_ready, endpoint, expected):
    """
    arrange: given s3 relation data.
    act: when to_relation_data is called.
    assert: expected relation data is returned.
    """
    charm: PaasCharm = generic_harness.charm
    monkeypatch.setattr(charm._tracing, "is_ready", MagicMock(return_value=is_ready))
    monkeypatch.setattr(charm._tracing, "get_endpoint", MagicMock(return_value=endpoint))

    assert charm._tracing.to_relation_data() == expected


def test_requirer_to_relation_data_protocol_not_request_error(generic_harness):
    """
    arrange: given a monkeypatched get_endpoint method that raises ProtocolNotRequestedError.
    act: when to_relation_data is called.
    assert: InvalidTracingRelationDataError is raised.
    """
    charm: PaasCharm = generic_harness.charm
    charm._tracing.is_ready = MagicMock(return_value=True)
    charm._tracing.get_endpoint = MagicMock(side_effect=ProtocolNotRequestedError)
    with pytest.raises(InvalidTracingRelationDataError) as exc:
        charm._tracing.to_relation_data()

    assert "Invalid PaaSTracingRelationData" in str(exc)


@pytest.mark.parametrize(
    "endpoint",
    [
        pytest.param("not_a_url", id="invalid URL"),
        pytest.param("http://invalid:port", id="invalid port"),
    ],
)
def test_requirer_to_validation_error(monkeypatch, generic_harness, endpoint):
    """
    arrange: given incomplete/invalid relation data.
    act: when to_relation_data is called.
    assert: InvalidTempoRelationDataError is raised.
    """
    charm: PaasCharm = generic_harness.charm
    monkeypatch.setattr(charm._tracing, "is_ready", MagicMock(return_value=True))
    monkeypatch.setattr(charm._tracing, "get_endpoint", MagicMock(return_value=endpoint))

    with pytest.raises(InvalidTracingRelationDataError) as exc:
        charm._tracing.to_relation_data()

    assert "invalid options" in str(exc.value)
