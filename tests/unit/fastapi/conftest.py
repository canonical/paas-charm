# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the fastapi unit test."""

import pathlib
import typing
from unittest import mock

import pytest
from ops import testing

from examples.fastapi.charm.src.charm import FastAPICharm
from paas_charm.paas_config import PaasConfig, read_paas_config

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
FASTAPI_CHARM_ROOT = PROJECT_ROOT / "examples/fastapi/charm"


@pytest.fixture(name="fastapi_context")
def fastapi_context_fixture(
    request: pytest.FixtureRequest,
) -> typing.Generator[testing.Context[FastAPICharm], None, None]:
    """Context rooted at the FastAPI example charm."""
    paas_config = typing.cast(PaasConfig | None, getattr(request, "param", None))
    if paas_config is None:
        paas_config = read_paas_config(FASTAPI_CHARM_ROOT)
    with (
        mock.patch("paas_charm.charm.read_paas_config", return_value=paas_config),
        testing.Context(FastAPICharm, charm_root=FASTAPI_CHARM_ROOT) as context,
    ):
        yield context


@pytest.fixture(name="base_state")
def base_state_fixture():
    """State with the FastAPI container and secret storage relation."""
    return {
        "leader": True,
        "secrets": [
            testing.Secret(
                tracked_content={"value": "test"},
                label="fastapi-secret-key",
                owner="app",
            )
        ],
        "relations": [
            testing.PeerRelation("peers"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                _base_plan=DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
        "config": {"non-optional-string": "non-optional-value"},
    }
