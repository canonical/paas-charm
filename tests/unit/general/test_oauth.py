# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm unit tests for Oauth relation."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=R0801


from secrets import token_hex
from unittest.mock import patch

import pytest
from conftest import OAUTH_RELATION_DATA_EXAMPLE
from ops import testing

from examples.django.charm.src.charm import DjangoCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.utils import config_metadata


@pytest.mark.parametrize(
    "base_state, charm, framework, config, command, env",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            "flask",
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app -k [ sync ]",
            {
                "FLASK_OIDC_REDIRECT_PATH": "/oauth/callback",
                "FLASK_OIDC_SCOPES": "openid profile email phone",
                "FLASK_PREFERRED_URL_SCHEME": "HTTPS",
                "FLASK_BASE_URL": "http://juju.test/",
                "FLASK_SECRET_KEY": "test",
                "FLASK_PEER_FQDNS": "flask-k8s-0.flask-k8s-endpoints.test-model.svc.cluster.local",
                "FLASK_OIDC_CLIENT_ID": "test-client-id",
                "FLASK_OIDC_CLIENT_SECRET": "abc",
                "FLASK_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "FLASK_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "FLASK_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "FLASK_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "FLASK_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "FLASK_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
            },
            id="flask-oidc",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            "django",
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application -k [ sync ]",
            {
                "DJANGO_OIDC_REDIRECT_PATH": "/oauth/callback",
                "DJANGO_OIDC_SCOPES": "openid profile email phone",
                "DJANGO_BASE_URL": "http://juju.test/",
                "DJANGO_SECRET_KEY": "test",
                "DJANGO_ALLOWED_HOSTS": '["juju.test"]',
                "DJANGO_PEER_FQDNS": "django-k8s-0.django-k8s-endpoints.test-model.svc.cluster.local",
                "DJANGO_OIDC_CLIENT_ID": "test-client-id",
                "DJANGO_OIDC_CLIENT_SECRET": "abc",
                "DJANGO_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "DJANGO_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "DJANGO_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "DJANGO_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "DJANGO_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "DJANGO_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/django-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "django-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/django-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="django-oidc",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            "fastapi",
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "non-optional-string": "test",
            },
            "/bin/python3 -m uvicorn app:app",
            {
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_BASE_URL": "http://juju.test/",
                "APP_SECRET_KEY": "test",
                "APP_NON_OPTIONAL_STRING": "test",
                "APP_PEER_FQDNS": "fastapi-k8s-0.fastapi-k8s-endpoints.test-model.svc.cluster.local",
                "APP_OIDC_CLIENT_ID": "test-client-id",
                "APP_OIDC_CLIENT_SECRET": "abc",
                "APP_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "APP_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "APP_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "APP_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "APP_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "APP_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "METRICS_PATH": "/metrics",
                "METRICS_PORT": "8080",
                "UVICORN_HOST": "0.0.0.0",
                "UVICORN_LOG_LEVEL": "info",
                "UVICORN_PORT": "8080",
                "WEB_CONCURRENCY": "1",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/fastapi-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "fastapi-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/fastapi-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="fastapi-oidc",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            "spring-boot",
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "oidc-user-name-attribute": "email",
            },
            'bash -c "java -jar *.jar"',
            {
                "APP_BASE_URL": "http://juju.test/",
                "APP_METRICS_PORT": "8080",
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_OIDC_USER_NAME_ATTRIBUTE": "email",
                "APP_PEER_FQDNS": "spring-boot-k8s-0.spring-boot-k8s-endpoints.test-model.svc.cluster.local",
                "APP_SECRET_KEY": "test",
                "MANAGEMENT_SERVER_PORT": "8080",
                "METRICS_PATH": "/actuator/prometheus",
                "OTEL_LOGS_EXPORTER": "none",
                "OTEL_METRICS_EXPORTER": "none",
                "OTEL_TRACES_EXPORTER": "none",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/spring-boot-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "spring-boot-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/spring-boot-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
                "SERVER_PORT": "8080",
                "management.endpoints.web.base-path": "/actuator",
                "management.endpoints.web.exposure.include": "prometheus",
                "management.endpoints.web.path-mapping.prometheus": "prometheus",
                "server.forward-headers-strategy": "framework",
                "spring.datasource.password": "test-password",
                "spring.datasource.url": "jdbc:postgresql://test-postgresql:5432/spring-boot-k8s",
                "spring.datasource.username": "test-username",
                "spring.jpa.hibernate.ddl-auto": "none",
                "spring.security.oauth2.client.provider.oidc.authorization-uri": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "spring.security.oauth2.client.provider.oidc.issuer-uri": "https://traefik_ip/model_name-hydra",
                "spring.security.oauth2.client.provider.oidc.jwk-set-uri": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "spring.security.oauth2.client.provider.oidc.token-uri": "https://traefik_ip/model_name-hydra/oauth2/token",
                "spring.security.oauth2.client.provider.oidc.user-info-uri": "https://traefik_ip/model_name-hydra/userinfo",
                "spring.security.oauth2.client.provider.oidc.user-name-attribute": "email",
                "spring.security.oauth2.client.registration.oidc.authorization-grant-type": "authorization_code",
                "spring.security.oauth2.client.registration.oidc.client-id": "test-client-id",
                "spring.security.oauth2.client.registration.oidc.client-secret": "abc",
                "spring.security.oauth2.client.registration.oidc.redirect-uri": "http://juju.test//oauth/callback",
                "spring.security.oauth2.client.registration.oidc.scope": "openid,profile,email,phone",
                "spring.security.oauth2.client.registration.oidc.user-name-attribute": "email",
            },
            id="spring-boot-oidc",
        ),
    ],
)
def test_oauth_config_wrong_relation_order(
    base_state: dict, charm, framework: str, config: dict, command: str, env: dict, request
) -> None:
    """
    arrange: set the workload charm config.
    act: start the workload charm and integrate with oauth.
    assert: workload charm should be blocked before the ingress integration and active after.
    """
    base_state = request.getfixturevalue(base_state)
    base_state["config"] = config
    secret_id = token_hex(16)
    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"] = [testing.Secret(id=secret_id, tracked_content={"secret": "abc"})]

    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=charm,
    )
    out = context.run(context.on.relation_changed(oauth_relation), state)

    assert out.unit_status == testing.BlockedStatus(
        "Ingress relation is required for OIDC to work correctly!"
    )

    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.ActiveStatus()
    service_layer = list(out.containers)[0].plan.services[framework].to_dict()
    assert service_layer == {
        "environment": env,
        "startup": "enabled",
        "override": "replace",
        "command": command,
    }


@pytest.mark.parametrize(
    "base_state, charm, framework, config, command, env",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            "flask",
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app -k [ sync ]",
            {
                "FLASK_OIDC_REDIRECT_PATH": "/oauth/callback",
                "FLASK_OIDC_SCOPES": "openid profile email phone",
                "FLASK_PREFERRED_URL_SCHEME": "HTTPS",
                "FLASK_BASE_URL": "http://juju.test/",
                "FLASK_SECRET_KEY": "test",
                "FLASK_PEER_FQDNS": "flask-k8s-0.flask-k8s-endpoints.test-model.svc.cluster.local",
                "FLASK_OIDC_CLIENT_ID": "test-client-id",
                "FLASK_OIDC_CLIENT_SECRET": "abc",
                "FLASK_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "FLASK_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "FLASK_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "FLASK_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "FLASK_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "FLASK_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
            },
            id="flask-oidc",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            "spring-boot",
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "oidc-user-name-attribute": "email",
            },
            'bash -c "java -jar *.jar"',
            {
                "APP_BASE_URL": "http://juju.test/",
                "APP_METRICS_PORT": "8080",
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_OIDC_USER_NAME_ATTRIBUTE": "email",
                "APP_PEER_FQDNS": "spring-boot-k8s-0.spring-boot-k8s-endpoints.test-model.svc.cluster.local",
                "APP_SECRET_KEY": "test",
                "MANAGEMENT_SERVER_PORT": "8080",
                "METRICS_PATH": "/actuator/prometheus",
                "OTEL_LOGS_EXPORTER": "none",
                "OTEL_METRICS_EXPORTER": "none",
                "OTEL_TRACES_EXPORTER": "none",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/spring-boot-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "spring-boot-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/spring-boot-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
                "SERVER_PORT": "8080",
                "management.endpoints.web.base-path": "/actuator",
                "management.endpoints.web.exposure.include": "prometheus",
                "management.endpoints.web.path-mapping.prometheus": "prometheus",
                "server.forward-headers-strategy": "framework",
                "spring.datasource.password": "test-password",
                "spring.datasource.url": "jdbc:postgresql://test-postgresql:5432/spring-boot-k8s",
                "spring.datasource.username": "test-username",
                "spring.jpa.hibernate.ddl-auto": "none",
                "spring.security.oauth2.client.provider.oidc.authorization-uri": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "spring.security.oauth2.client.provider.oidc.issuer-uri": "https://traefik_ip/model_name-hydra",
                "spring.security.oauth2.client.provider.oidc.jwk-set-uri": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "spring.security.oauth2.client.provider.oidc.token-uri": "https://traefik_ip/model_name-hydra/oauth2/token",
                "spring.security.oauth2.client.provider.oidc.user-info-uri": "https://traefik_ip/model_name-hydra/userinfo",
                "spring.security.oauth2.client.provider.oidc.user-name-attribute": "email",
                "spring.security.oauth2.client.registration.oidc.authorization-grant-type": "authorization_code",
                "spring.security.oauth2.client.registration.oidc.client-id": "test-client-id",
                "spring.security.oauth2.client.registration.oidc.client-secret": "abc",
                "spring.security.oauth2.client.registration.oidc.redirect-uri": "http://juju.test//oauth/callback",
                "spring.security.oauth2.client.registration.oidc.scope": "openid,profile,email,phone",
                "spring.security.oauth2.client.registration.oidc.user-name-attribute": "email",
            },
            id="spring-boot-oidc",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            "django",
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application -k [ sync ]",
            {
                "DJANGO_OIDC_REDIRECT_PATH": "/oauth/callback",
                "DJANGO_OIDC_SCOPES": "openid profile email phone",
                "DJANGO_BASE_URL": "http://juju.test/",
                "DJANGO_SECRET_KEY": "test",
                "DJANGO_ALLOWED_HOSTS": '["juju.test"]',
                "DJANGO_PEER_FQDNS": "django-k8s-0.django-k8s-endpoints.test-model.svc.cluster.local",
                "DJANGO_OIDC_CLIENT_ID": "test-client-id",
                "DJANGO_OIDC_CLIENT_SECRET": "abc",
                "DJANGO_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "DJANGO_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "DJANGO_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "DJANGO_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "DJANGO_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "DJANGO_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/django-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "django-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/django-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="django-oidc",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            "fastapi",
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "non-optional-string": "test",
            },
            "/bin/python3 -m uvicorn app:app",
            {
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_BASE_URL": "http://juju.test/",
                "APP_SECRET_KEY": "test",
                "APP_NON_OPTIONAL_STRING": "test",
                "APP_PEER_FQDNS": "fastapi-k8s-0.fastapi-k8s-endpoints.test-model.svc.cluster.local",
                "APP_OIDC_CLIENT_ID": "test-client-id",
                "APP_OIDC_CLIENT_SECRET": "abc",
                "APP_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "APP_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "APP_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "APP_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "APP_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "APP_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "METRICS_PATH": "/metrics",
                "METRICS_PORT": "8080",
                "UVICORN_HOST": "0.0.0.0",
                "UVICORN_LOG_LEVEL": "info",
                "UVICORN_PORT": "8080",
                "WEB_CONCURRENCY": "1",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/fastapi-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "fastapi-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/fastapi-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="fastapi-oidc",
        ),
    ],
)
def test_oauth_config_correct_relation_order(
    base_state: dict, charm, framework: str, config: dict, command: str, env: dict, request
) -> None:
    """
    arrange: set the workload charm config.
    act: start the workload charm and integrate with ingress and oauth.
    assert: workload charm should be active.
    """
    base_state = request.getfixturevalue(base_state)
    base_state["config"] = config
    secret_id = token_hex(16)
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=charm,
    )
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.ActiveStatus()

    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"] = [testing.Secret(id=secret_id, tracked_content={"secret": "abc"})]

    state = testing.State(**base_state)
    out = context.run(context.on.relation_changed(oauth_relation), state)
    service_layer = list(out.containers)[0].plan.services[framework].to_dict()
    assert service_layer == {
        "environment": env,
        "startup": "enabled",
        "override": "replace",
        "command": command,
    }


@pytest.mark.parametrize(
    "base_state, charm, config",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            id="flask-oidc",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            id="django-oidc",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "non-optional-string": "test",
            },
            id="fastapi-oidc",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "oidc-user-name-attribute": "email",
            },
            id="spring-boot-oidc",
        ),
    ],
)
def test_oauth_config_remove_ingress_integration_should_block(
    base_state: dict, charm, config: dict, request
) -> None:
    """
    arrange: set the workload charm config.
    act: start the workload charm and integrate with oauth and ingress.
    assert: workload charm should be blocked after removing the ingress integration.
    """
    base_state = request.getfixturevalue(base_state)
    base_state["config"] = config
    secret_id = token_hex(16)
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=charm,
    )
    out = context.run(context.on.relation_changed(ingress_relation), state)

    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"] = [testing.Secret(id=secret_id, tracked_content={"secret": "abc"})]

    state = testing.State(**base_state)
    out = context.run(context.on.relation_changed(oauth_relation), state)
    assert out.unit_status == testing.ActiveStatus()
    base_state["relations"].remove(ingress_relation)

    state = testing.State(**base_state)
    out = context.run(context.on.relation_changed(oauth_relation), state)
    assert out.unit_status == testing.BlockedStatus(
        "Ingress relation is required for OIDC to work correctly!"
    )


@pytest.mark.parametrize(
    "base_state, charm, config",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            id="flask-oidc",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            id="django-oidc",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "non-optional-string": "test",
            },
            id="fastapi-oidc",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "oidc-user-name-attribute": "email",
            },
            id="spring-boot-oidc",
        ),
    ],
)
def test_oauth_config_remove_oauth_integration_should_not_block(
    base_state: dict, charm, config: dict, request
) -> None:
    """
    arrange: set the workload charm config.
    act: start the workload charm and integrate with oauth and ingress.
    assert: workload charm should be active after removing the oauth integration.
    """
    base_state = request.getfixturevalue(base_state)
    base_state["config"] = config
    secret_id = token_hex(16)
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=charm,
    )
    out = context.run(context.on.relation_changed(ingress_relation), state)

    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"] = [testing.Secret(id=secret_id, tracked_content={"secret": "abc"})]

    state = testing.State(**base_state)
    out = context.run(context.on.relation_changed(oauth_relation), state)
    assert out.unit_status == testing.ActiveStatus()
    base_state["relations"].remove(oauth_relation)

    state = testing.State(**base_state)
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.ActiveStatus()


@pytest.mark.parametrize(
    "base_state, charm, config",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "profile email phone",
            },
            id="flask-oidc-fail",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "profile email phone",
            },
            id="django-oidc",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "profile email phone",
                "non-optional-string": "test",
            },
            id="fastapi-oidc",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "profile email phone",
                "oidc-user-name-attribute": "email",
            },
            id="spring-boot-oidc",
        ),
    ],
)
def test_oauth_config_wrong_scope(base_state: dict, charm, config: dict, request) -> None:
    """
    arrange: set the workload charm config.
    act: start the workload charm and integrate with oauth and ingress using wrong scope.
    assert: workload charm should be blocked.
    """
    base_state = request.getfixturevalue(base_state)
    base_state["config"] = config
    secret_id = token_hex(16)
    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"] = [testing.Secret(id=secret_id, tracked_content={"secret": "abc"})]
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=charm,
    )
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.BlockedStatus(
        "The 'openid' scope is required for OAuth integration, please add it to the scopes."
    )


@pytest.mark.parametrize(
    "base_state, charm, config",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            id="flask-oidc",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
            },
            id="django-oidc",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "non-optional-string": "test",
            },
            id="fastapi-oidc",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "oidc-user-name-attribute": "email",
            },
            id="spring-boot-oidc",
        ),
    ],
)
def test_blocked_when_relation_data_empty(base_state: dict, charm, config: dict, request) -> None:
    """
    arrange: set the workload charm config.
    act: start the workload charm and integrate with oauth and ingress using wrong scope.
    assert: workload charm should be blocked.
    """
    base_state = request.getfixturevalue(base_state)
    base_state["config"] = config
    secret_id = token_hex(16)
    oauth_relation = testing.Relation(
        endpoint="oidc", interface="oauth", remote_app_data={}, remote_app_name="OIDC_CHARM"
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"] = [testing.Secret(id=secret_id, tracked_content={"secret": "abc"})]
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=charm,
    )
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.BlockedStatus("Please check OIDC_CHARM charm!")


@pytest.mark.parametrize(
    "base_state, charm, config, multiple_oauth_integrations",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "google-redirect-path": "/oauth/callback",
                "google-scopes": "openid profile email phone",
            },
            {"framework": "flask"},
            id="flask",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "google-redirect-path": "/oauth/callback",
                "google-scopes": "openid profile email phone",
            },
            {"framework": "django"},
            id="django",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "oidc-user-name-attribute": "email",
                "google-redirect-path": "/oauth/callback",
                "google-scopes": "openid profile email phone",
                "google-user-name-attribute": "email",
            },
            {"framework": "springboot"},
            id="spring-boot",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "oidc-redirect-path": "/oauth/callback",
                "oidc-scopes": "openid profile email phone",
                "non-optional-string": "test",
                "google-redirect-path": "/oauth/callback",
                "google-scopes": "openid profile email phone",
            },
            {"framework": "fastapi"},
            id="fastapi-oidc",
        ),
    ],
    indirect=["multiple_oauth_integrations"],
)
def test_oauth_multiple_oauth_integrations(
    base_state: dict, multiple_oauth_integrations, charm, config: dict, request
) -> None:
    """
    arrange: set the workload charm config.
    act: start the workload charm and integrate with oauth and ingress using wrong scope.
    assert: workload charm should be blocked.
    """
    base_state = request.getfixturevalue(base_state)
    base_state["config"] = config
    secret_id = token_hex(16)
    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"] = [testing.Secret(id=secret_id, tracked_content={"secret": "abc"})]
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=charm,
    )
    # `config_metadata` function is cached and we modify the metadata
    # in the `multiple_oauth_integrations` fixture
    with patch("paas_charm.utils.config_metadata", new=config_metadata.__wrapped__):
        out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.BlockedStatus(
        "Multiple OAuth relations are not supported at the moment"
    )
