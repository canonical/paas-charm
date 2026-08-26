# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the Springboot unit test."""

import pathlib
import typing
from unittest import mock

import pytest
from ops import testing

from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.paas_config import read_paas_config
from tests.unit.conftest import postgresql_relation

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
SPRINGBOOT_CHARM_ROOT = PROJECT_ROOT / "examples/springboot/charm"


@pytest.fixture(name="springboot_context")
def springboot_context_fixture() -> typing.Generator[testing.Context[SpringBootCharm], None, None]:
    """Context rooted at the Spring Boot example charm."""
    with (
        mock.patch(
            "paas_charm.charm.read_paas_config",
            return_value=read_paas_config(SPRINGBOOT_CHARM_ROOT),
        ),
        testing.Context(SpringBootCharm, charm_root=SPRINGBOOT_CHARM_ROOT) as context,
    ):
        yield context


@pytest.fixture(name="base_state")
def base_state_fixture():
    """State with container and config file set."""
    return {
        "leader": True,
        "secrets": [
            testing.Secret(
                tracked_content={"value": "test"},
                label="app-secret-key",
                owner="app",
            )
        ],
        "relations": [
            testing.PeerRelation("peers"),
            postgresql_relation("spring-boot-k8s"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/app/saml.cert", source="cert")},
                _base_plan=DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(name="mysql_relation")
def mysql_relation_fixture():
    """MySQL relation fixture."""
    relation_data = {
        "database": "spring-boot-k8s",
        "endpoints": "test-mysql:3306",
        "password": "test-password",
        "username": "test-username",
    }
    return testing.Relation(
        endpoint="mysql",
        interface="mysql_client",
        remote_app_data=relation_data,
    )


@pytest.fixture(name="mysql_base_state")
def base_state_fixture_with_mysql(mysql_relation):
    """State with container and config file set."""
    return {
        "leader": True,
        "secrets": [
            testing.Secret(
                tracked_content={"value": "test"},
                label="app-secret-key",
                owner="app",
            )
        ],
        "relations": [
            testing.PeerRelation("peers"),
            mysql_relation,
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/app/saml.cert", source="cert")},
                _base_plan=DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
    }
