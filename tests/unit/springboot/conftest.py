# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""pytest fixtures for the Springboot unit test."""

import pytest
from ops import testing


@pytest.fixture(name="base_state")
def base_state_fixture(spring_boot_framework_state):
    """Expose the focused Spring Boot state under the framework-local name."""
    return spring_boot_framework_state


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
def base_state_fixture_with_mysql(spring_boot_framework_state, mysql_relation):
    """Return the Spring Boot state with MySQL replacing PostgreSQL."""
    spring_boot_framework_state["relations"] = [
        relation
        for relation in spring_boot_framework_state["relations"]
        if relation.endpoint != "postgresql"
    ]
    spring_boot_framework_state["relations"].append(mysql_relation)
    return spring_boot_framework_state
