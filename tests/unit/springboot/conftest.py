# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the Springboot unit test."""
import os
import pathlib

import pytest
from ops import testing

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True, scope="package")
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/springboot/charm")


@pytest.fixture(name="postgresql_relation")
def postgresql_relation_fixture():
    """Postgresql relation fixture."""
    relation_data = {
        "database": "spring-boot-k8s",
        "endpoints": "test-postgresql:5432",
        "password": "test-password",
        "username": "test-username",
    }
    yield testing.Relation(
        endpoint="postgresql",
        interface="postgresql_client",
        remote_app_data=relation_data,
    )


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture(postgresql_relation):
    """State with container and config file set."""
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"spring-boot_secret_key": "test"}
            ),
            postgresql_relation,
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
