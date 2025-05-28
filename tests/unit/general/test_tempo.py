# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tempo lib wrapper unit tests."""

from unittest.mock import MagicMock

import pytest

from paas_charm.charm import PaasCharm
from paas_charm.tempo import InvalidTempoRelationDataError, PaaSTempoRelationData


@pytest.mark.parametrize(
    "is_ready, endpoint, expected",
    [
        pytest.param(False, None, None, id="Not ready"),
        pytest.param(True, "", None, id="No endpoint data"),
        pytest.param(
            True,
            "http://test-endpoint.test",
            PaaSTempoRelationData(endpoint="http://test-endpoint.test", service_name="flask-k8s"),
            id="No endpoint data",
        ),
    ],
)
def test_requirer_to_relation_data(monkeypatch, flask_harness, is_ready, endpoint, expected):
    """
    arrange: given s3 relation data.
    act: when to_relation_data is called.
    assert: expected relation data is returned.
    """
    flask_harness.begin()
    charm: PaasCharm = flask_harness.charm
    monkeypatch.setattr(charm._tracing, "is_ready", MagicMock(return_value=is_ready))
    monkeypatch.setattr(charm._tracing, "get_endpoint", MagicMock(return_value=endpoint))

    assert charm._tracing.to_relation_data() == expected


@pytest.mark.parametrize(
    "endpoint",
    [
        pytest.param("not_a_url", id="invalid URL"),
        pytest.param("http://invalid:port", id="invalid port"),
    ],
)
def test_requirer_to_validation_error(monkeypatch, flask_harness, endpoint):
    """
    arrange: given incomplete/invalid relation data.
    act: when to_relation_data is called.
    assert: InvalidTempoRelationDataError is raised.
    """
    flask_harness.begin()
    charm: PaasCharm = flask_harness.charm
    monkeypatch.setattr(charm._tracing, "is_ready", MagicMock(return_value=True))
    monkeypatch.setattr(charm._tracing, "get_endpoint", MagicMock(return_value=endpoint))

    with pytest.raises(InvalidTempoRelationDataError) as exc:
        charm._tracing.to_relation_data()

    assert "Tempo" in str(exc.value)
