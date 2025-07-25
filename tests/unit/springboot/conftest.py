# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the Springboot unit test."""
import os
import pathlib

import pytest
from ops import testing

from tests.unit.conftest import postgresql_relation

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/springboot/charm")


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture():
    """State with container and config file set."""
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"spring-boot_secret_key": "test"}
            ),
            postgresql_relation("spring-boot-k8s"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/app/saml.cert", source="cert")},
                _base_plan={
                    "services": {
                        "spring-boot": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": 'bash -c "java -jar *.jar"',
                        }
                    }
                },
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
    yield testing.Relation(
        endpoint="mysql",
        interface="mysql_client",
        remote_app_data=relation_data,
    )


@pytest.fixture(scope="function", name="mysql_base_state")
def base_state_fixture_with_mysql(mysql_relation):
    """State with container and config file set."""
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"spring-boot_secret_key": "test"}
            ),
            mysql_relation,
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/app/saml.cert", source="cert")},
                _base_plan={
                    "services": {
                        "spring-boot": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": 'bash -c "java -jar *.jar"',
                        }
                    }
                },
            )
        },
        "model": testing.Model(name="test-model"),
    }
