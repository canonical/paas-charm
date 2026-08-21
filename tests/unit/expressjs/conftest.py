# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the ExpressJS unit test."""

import pathlib
import typing
from unittest import mock

import pytest
import yaml
from ops import testing

from examples.expressjs.charm.src.charm import ExpressJSCharm
from paas_charm.paas_config import read_paas_config
from tests.unit.conftest import postgresql_relation

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parents[3]
EXPRESSJS_CHARM_ROOT = PROJECT_ROOT / "examples" / "expressjs" / "charm"


@pytest.fixture(name="expressjs_context")
def expressjs_context_fixture() -> typing.Generator[testing.Context[ExpressJSCharm], None, None]:
    """Provide a lifecycle-managed Context rooted at the ExpressJS example charm."""
    charmcraft = yaml.safe_load((EXPRESSJS_CHARM_ROOT / "charmcraft.yaml").read_text())
    actions = charmcraft.pop("actions")
    config = charmcraft.pop("config")
    with (
        mock.patch(
            "paas_charm.charm.read_paas_config",
            return_value=read_paas_config(EXPRESSJS_CHARM_ROOT),
        ),
        testing.Context(
            ExpressJSCharm,
            meta=charmcraft,
            actions=actions,
            config=config,
            charm_root=EXPRESSJS_CHARM_ROOT,
        ) as context,
    ):
        yield context


@pytest.fixture(name="base_state")
def base_state_fixture():
    """State with the ExpressJS container and required relations."""
    return {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"expressjs_secret_key": "test"}
            ),
            postgresql_relation("test-database"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                _base_plan=DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
    }
