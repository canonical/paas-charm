# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Springboot charm unit tests."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801

import json

import pytest
from ops import testing

from paas_charm.relations import CustomRelation
from paas_charm.springboot.charm import SpringValkeyRelation
from paas_charm.valkey import ValkeyRelation


class _SampleRelation(CustomRelation):
    """Sample relation used as a placeholder when overriding builtin relations."""

    relation_name = "sample"

    def setup(self, on_change) -> None:  # pylint: disable=unused-argument
        """No-op setup."""

    def gen_environment(self) -> dict[str, str]:
        """Return no environment variables."""
        return {}


@pytest.mark.parametrize(
    "config, env",
    [
        pytest.param(
            {},
            {
                "SERVER_PORT": "8080",
                "APP_OIDC_REDIRECT_PATH": "/login/oauth2/code/oidc",
                "APP_OIDC_SCOPES": "openid profile email",
                "APP_OIDC_USER_NAME_ATTRIBUTE": "sub",
                "management.endpoints.web.exposure.include": "prometheus",
                "management.server.port": "8080",
                "management.endpoints.web.base-path": "/actuator",
                "management.endpoints.web.path-mapping.prometheus": "prometheus",
                "APP_BASE_URL": "http://spring-boot-k8s.test-model:8080",
                "APP_SECRET_KEY": "test",
                "spring.datasource.username": "test-username",
                "spring.datasource.password": "test-password",
                "spring.datasource.url": "jdbc:postgresql://test-postgresql:5432/spring-boot-k8s",
                "spring.jpa.hibernate.ddl-auto": "none",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/spring-boot-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PATH": "/spring-boot-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_USERNAME": "test-username",
                "POSTGRESQL_DB_NAME": "spring-boot-k8s",
                "OTEL_LOGS_EXPORTER": "none",
                "OTEL_METRICS_EXPORTER": "none",
                "OTEL_TRACES_EXPORTER": "none",
                "server.forward-headers-strategy": "framework",
            },
            id="default",
        ),
        pytest.param(
            {
                "app-profiles": "dev,postgresql",
            },
            {
                "SERVER_PORT": "8080",
                "APP_BASE_URL": "http://spring-boot-k8s.test-model:8080",
                "APP_OIDC_REDIRECT_PATH": "/login/oauth2/code/oidc",
                "APP_OIDC_SCOPES": "openid profile email",
                "APP_OIDC_USER_NAME_ATTRIBUTE": "sub",
                "management.endpoints.web.exposure.include": "prometheus",
                "management.server.port": "8080",
                "management.endpoints.web.base-path": "/actuator",
                "management.endpoints.web.path-mapping.prometheus": "prometheus",
                "APP_SECRET_KEY": "test",
                "spring.datasource.username": "test-username",
                "spring.datasource.password": "test-password",
                "spring.datasource.url": "jdbc:postgresql://test-postgresql:5432/spring-boot-k8s",
                "spring.jpa.hibernate.ddl-auto": "none",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/spring-boot-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PATH": "/spring-boot-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_USERNAME": "test-username",
                "POSTGRESQL_DB_NAME": "spring-boot-k8s",
                "OTEL_LOGS_EXPORTER": "none",
                "OTEL_METRICS_EXPORTER": "none",
                "OTEL_TRACES_EXPORTER": "none",
                "server.forward-headers-strategy": "framework",
                "APP_PROFILES": "dev,postgresql",
                "spring.profiles.active": "dev,postgresql",
            },
            id="custom config",
        ),
    ],
)
def test_springboot_config(springboot_context, base_state, config: dict, env: dict) -> None:
    """
    arrange: set the springboot charm config.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: springboot charm should submit the correct springboot pebble layer to pebble.
    """
    base_state["config"] = config
    state = testing.State(**base_state)
    out = springboot_context.run(springboot_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()

    springboot_layer = out.get_container("app").plan.services["spring-boot"].to_dict()
    assert springboot_layer == {
        "environment": env,
        "startup": "enabled",
        "override": "replace",
        "command": 'bash -c "java -jar *.jar"',
    }


def test_metrics_config(
    springboot_context,
    base_state,
) -> None:
    """
    arrange: add a Prometheus scrape relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: relation data should contain the Spring Boot unit and workload scrape endpoint.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="metrics-endpoint",
            interface="prometheus_scrape",
        )
    )
    state = testing.State(**base_state)

    out = springboot_context.run(springboot_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()

    metrics_endpoint_relation = out.get_relations("metrics-endpoint")
    assert len(metrics_endpoint_relation) == 1

    relation_data_unit = metrics_endpoint_relation[0].local_unit_data
    assert relation_data_unit["prometheus_scrape_unit_address"]
    assert relation_data_unit["prometheus_scrape_unit_name"] == "spring-boot-k8s/0"
    assert json.loads(metrics_endpoint_relation[0].local_app_data["scrape_jobs"]) == [
        {
            "metrics_path": "/actuator/prometheus",
            "static_configs": [{"targets": ["*:8080"]}],
        }
    ]


@pytest.mark.parametrize(
    "builtin_relations, expected",
    [
        pytest.param(
            [ValkeyRelation],
            [SpringValkeyRelation],
            id="valkey replaced",
        ),
        pytest.param(
            [],
            [],
            id="no builtin relations",
        ),
        pytest.param(
            [_SampleRelation, ValkeyRelation],
            [_SampleRelation, SpringValkeyRelation],
            id="other relations preserved",
        ),
        pytest.param(
            [SpringValkeyRelation],
            [SpringValkeyRelation],
            id="idempotent",
        ),
    ],
)
def test_override_builtin_relations(
    springboot_context,
    base_state,
    builtin_relations: list[type[CustomRelation]],
    expected: list[type[CustomRelation]],
) -> None:
    """
    arrange: a springboot charm with a set of builtin relation classes.
    act: call the builtin relations override hook with the given relation classes.
    assert: ValkeyRelation is replaced by SpringValkeyRelation while any other
        relation class is left untouched.
    """
    state = testing.State(**base_state)
    with springboot_context(springboot_context.on.config_changed(), state) as manager:
        assert manager.charm._override_builtin_relations(builtin_relations) == expected
        manager.run()


def test_builtin_valkey_relation_is_spring_valkey(springboot_context, base_state) -> None:
    """
    arrange: a springboot charm with the valkey integration in its metadata.
    act: initialize the springboot charm.
    assert: the builtin valkey relation is instantiated as SpringValkeyRelation.
    """
    state = testing.State(**base_state)
    with springboot_context(springboot_context.on.config_changed(), state) as manager:
        valkey_relations = [
            relation
            for relation in manager.charm._custom_relations
            if relation.relation_name == "valkey"
        ]
        assert [type(relation) for relation in valkey_relations] == [SpringValkeyRelation]
        out = manager.run()

    assert out.unit_status == testing.ActiveStatus()
