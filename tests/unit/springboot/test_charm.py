# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Springboot charm unit tests."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801


import pytest
from ops import testing

from examples.springboot.charm.src.charm import SpringBootCharm


@pytest.mark.parametrize(
    "config, env",
    [
        pytest.param(
            {},
            {
                "SERVER_PORT": "8080",
                "MANAGEMENT_SERVER_PORT": "8080",
                "APP_METRICS_PORT": "8080",
                "APP_OIDC_REDIRECT_PATH": "/login/oauth2/code/oidc",
                "APP_OIDC_SCOPES": "openid profile email",
                "APP_OIDC_USER_NAME_ATTRIBUTE": "sub",
                "METRICS_PATH": "/actuator/prometheus",
                "management.endpoints.web.exposure.include": "prometheus",
                "management.endpoints.web.base-path": "/actuator",
                "management.endpoints.web.path-mapping.prometheus": "prometheus",
                "APP_BASE_URL": "http://spring-boot-k8s.test-model:8080",
                "APP_SECRET_KEY": "test",
                "APP_PEER_FQDNS": "spring-boot-k8s-0.spring-boot-k8s-endpoints.test-model.svc.cluster.local",
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
                "app-port": 9000,
                "metrics-port": 9001,
                "metrics-path": "/othermetrics",
                "app-profiles": "dev,postgresql",
            },
            {
                "SERVER_PORT": "9000",
                "APP_BASE_URL": "http://spring-boot-k8s.test-model:9000",
                "APP_METRICS_PORT": "9001",
                "APP_OIDC_REDIRECT_PATH": "/login/oauth2/code/oidc",
                "APP_OIDC_SCOPES": "openid profile email",
                "APP_OIDC_USER_NAME_ATTRIBUTE": "sub",
                "MANAGEMENT_SERVER_PORT": "9001",
                "METRICS_PATH": "/othermetrics",
                "management.endpoints.web.exposure.include": "prometheus",
                "management.endpoints.web.base-path": "/",
                "management.endpoints.web.path-mapping.prometheus": "othermetrics",
                "APP_SECRET_KEY": "test",
                "APP_PEER_FQDNS": "spring-boot-k8s-0.spring-boot-k8s-endpoints.test-model.svc.cluster.local",
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
def test_springboot_config(base_state, config: dict, env: dict) -> None:
    """
    arrange: set the springboot charm config.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: springboot charm should submit the correct springboot pebble layer to pebble.
    """
    base_state["config"] = config
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=SpringBootCharm,
    )
    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()

    springboot_layer = list(out.containers)[0].plan.services["spring-boot"].to_dict()
    assert springboot_layer == {
        "environment": env,
        "startup": "enabled",
        "override": "replace",
        "command": 'bash -c "java -jar *.jar"',
    }


def test_metrics_config(
    base_state,
) -> None:
    """
    arrange: add prometheus-k8s relation to the base state.
    act: start the springboot charm and set springboot-app container to be ready.
    assert: prometheus-k8s relation should have the springboot charm unit name.
    """
    base_state["relations"].append(
        testing.Relation(
            endpoint="metrics-endpoint",
            interface="prometheus-k8s",
        )
    )
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=SpringBootCharm,
    )

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()

    metrics_endpoint_relation = out.get_relations("metrics-endpoint")
    assert len(metrics_endpoint_relation) == 1

    relation_data_unit = metrics_endpoint_relation[0].local_unit_data
    assert relation_data_unit["prometheus_scrape_unit_address"]
    assert relation_data_unit["prometheus_scrape_unit_name"] == "spring-boot-k8s/0"
