# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm unit tests for Oauth relation."""

# Very similar cases to other frameworks. Disable duplicated checks.
# pylint: disable=duplicate-code,too-many-lines


from secrets import token_hex

import pytest
import yaml
from ops import testing

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.app import generate_oauth_env
from paas_charm.exceptions import PaasConfigError
from paas_charm.oauth import PaaSOAuthRelationData
from paas_charm.paas_config import (
    CONFIG_FILE_NAME,
    OAuthRelationConfig,
    PaasConfig,
    read_paas_config,
)
from tests.unit.general.constants import OAUTH_RELATION_DATA_EXAMPLE


def test_hyphenated_endpoint_config_environment():
    """Keep normalized names for the redirect path and scope of a hyphenated endpoint."""
    relation_data = PaaSOAuthRelationData.model_validate(
        {
            **OAUTH_RELATION_DATA_EXAMPLE,
            "provider_name": "company-login",
            "client_secret": "secret",
            "scopes": "openid email",
            "redirect_uri": "https://app.example/callback",
            "redirect_path": "/callback",
            "user_name_attribute": "sub",
        }
    )
    env = generate_oauth_env("go", relation_data)
    assert env["APP_COMPANY_LOGIN_REDIRECT_PATH"] == "/callback"
    assert env["APP_COMPANY_LOGIN_SCOPES"] == "openid email"


def _oauth_paas_config(root) -> PaasConfig:
    """Return the example paas-config.yaml with custom OAuth settings for the oidc endpoint."""
    return read_paas_config(root).model_copy(
        update={
            "relations": {
                "oidc": OAuthRelationConfig(
                    redirect_path="/oauth/callback",
                    scopes=["openid", "profile", "email", "phone"],
                )
            }
        }
    )


@pytest.mark.parametrize(
    "base_state, charm, framework, config, command, env",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            "flask",
            {},
            "/bin/python3 -m gunicorn -c /var/lib/gunicorn/gunicorn.conf.py app:app -k [ sync ]",
            {
                "FLASK_OIDC_REDIRECT_PATH": "/oauth/callback",
                "FLASK_OIDC_SCOPES": "openid profile email phone",
                "FLASK_PREFERRED_URL_SCHEME": "HTTPS",
                "FLASK_METRICS_PORT": "9102",
                "FLASK_METRICS_PATH": "/metrics",
                "FLASK_BASE_URL": "http://juju.test/",
                "FLASK_SECRET_KEY": "test",
                "FLASK_OIDC_CLIENT_ID": "test-client-id",
                "FLASK_OIDC_CLIENT_SECRET": "abc",
                "FLASK_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "FLASK_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "FLASK_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "FLASK_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "FLASK_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "FLASK_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
            },
            id="flask",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            "django",
            {},
            "/bin/python3 -m gunicorn -c /var/lib/gunicorn/gunicorn.conf.py django_app.wsgi:application -k [ sync ]",
            {
                "DJANGO_OIDC_REDIRECT_PATH": "/oauth/callback",
                "DJANGO_OIDC_SCOPES": "openid profile email phone",
                "DJANGO_BASE_URL": "http://juju.test/",
                "DJANGO_SECRET_KEY": "test",
                "DJANGO_ALLOWED_HOSTS": '["juju.test"]',
                "DJANGO_METRICS_PORT": "9102",
                "DJANGO_METRICS_PATH": "/metrics",
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
            id="django",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            "fastapi",
            {
                "non-optional-string": "test",
            },
            "/bin/python3 -m uvicorn app:app",
            {
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_BASE_URL": "http://juju.test/",
                "APP_SECRET_KEY": "test",
                "APP_NON_OPTIONAL_STRING": "test",
                "APP_OIDC_CLIENT_ID": "test-client-id",
                "APP_OIDC_CLIENT_SECRET": "abc",
                "APP_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "APP_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "APP_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "APP_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "APP_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "APP_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "UVICORN_HOST": "0.0.0.0",
                "UVICORN_LOG_LEVEL": "info",
                "UVICORN_PORT": "8000",
                "METRICS_PORT": "9464",
                "METRICS_PATH": "/metrics",
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
                "PYTHONPATH": "/tmp/fastapi/log_config",
                "UVICORN_LOG_CONFIG": "/tmp/fastapi/log_config/uvicorn-log-config.json",
            },
            id="fastapi",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            "spring-boot",
            {
                "oidc-user-name-attribute": "email",
            },
            'bash -c "java -jar *.jar"',
            {
                "APP_BASE_URL": "http://juju.test/",
                "APP_OIDC_USER_NAME_ATTRIBUTE": "email",
                "APP_SECRET_KEY": "test",
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
                "management.endpoints.web.exposure.include": "prometheus",
                "management.server.port": "8080",
                "management.endpoints.web.base-path": "/actuator",
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
                "spring.security.oauth2.client.registration.oidc.redirect-uri": "http://juju.test/oauth/callback",
                "spring.security.oauth2.client.registration.oidc.scope": "openid,profile,email,phone",
                "spring.security.oauth2.client.registration.oidc.user-name-attribute": "email",
            },
            id="spring-boot",
        ),
        pytest.param(
            "go_base_state",
            GoCharm,
            "go",
            {},
            "go-app",
            {
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_BASE_URL": "http://juju.test/",
                "APP_SECRET_KEY": "test",
                "APP_OIDC_CLIENT_ID": "test-client-id",
                "APP_OIDC_CLIENT_SECRET": "abc",
                "APP_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "APP_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "APP_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "APP_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "APP_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "APP_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "PORT": "8080",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/go-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "go-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/go-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="go",
        ),
        pytest.param(
            "expressjs_base_state",
            ExpressJSCharm,
            "expressjs",
            {},
            "npm start",
            {
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_BASE_URL": "http://juju.test/",
                "APP_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "APP_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "APP_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "APP_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "APP_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "APP_OIDC_CLIENT_ID": "test-client-id",
                "APP_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "APP_OIDC_CLIENT_SECRET": "abc",
                "NODE_ENV": "production",
                "APP_SECRET_KEY": "test",
                "PORT": "8080",
                "METRICS_PORT": "9464",
                "METRICS_PATH": "/metrics",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/expressjs-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "expressjs-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/expressjs-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="expressjs",
        ),
    ],
)
def test_oauth_config_wrong_relation_order(
    base_state: dict,
    charm,
    framework: str,
    config: dict,
    command: str,
    env: dict,
    request,
    context_factory,
    charm_root,
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
    base_state["secrets"].append(testing.Secret(id=secret_id, tracked_content={"secret": "abc"}))

    state = testing.State(**base_state)
    context = context_factory(charm, paas_config=_oauth_paas_config(charm_root(charm)))
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
            {},
            "/bin/python3 -m gunicorn -c /var/lib/gunicorn/gunicorn.conf.py app:app -k [ sync ]",
            {
                "FLASK_OIDC_REDIRECT_PATH": "/oauth/callback",
                "FLASK_OIDC_SCOPES": "openid profile email phone",
                "FLASK_PREFERRED_URL_SCHEME": "HTTPS",
                "FLASK_METRICS_PORT": "9102",
                "FLASK_METRICS_PATH": "/metrics",
                "FLASK_BASE_URL": "http://juju.test/",
                "FLASK_SECRET_KEY": "test",
                "FLASK_OIDC_CLIENT_ID": "test-client-id",
                "FLASK_OIDC_CLIENT_SECRET": "abc",
                "FLASK_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "FLASK_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "FLASK_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "FLASK_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "FLASK_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "FLASK_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
            },
            id="flask",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            "spring-boot",
            {
                "oidc-user-name-attribute": "email",
            },
            'bash -c "java -jar *.jar"',
            {
                "APP_BASE_URL": "http://juju.test/",
                "APP_OIDC_USER_NAME_ATTRIBUTE": "email",
                "APP_SECRET_KEY": "test",
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
                "management.endpoints.web.exposure.include": "prometheus",
                "management.server.port": "8080",
                "management.endpoints.web.base-path": "/actuator",
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
                "spring.security.oauth2.client.registration.oidc.redirect-uri": "http://juju.test/oauth/callback",
                "spring.security.oauth2.client.registration.oidc.scope": "openid,profile,email,phone",
                "spring.security.oauth2.client.registration.oidc.user-name-attribute": "email",
            },
            id="spring-boot",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            "django",
            {},
            "/bin/python3 -m gunicorn -c /var/lib/gunicorn/gunicorn.conf.py django_app.wsgi:application -k [ sync ]",
            {
                "DJANGO_OIDC_REDIRECT_PATH": "/oauth/callback",
                "DJANGO_OIDC_SCOPES": "openid profile email phone",
                "DJANGO_BASE_URL": "http://juju.test/",
                "DJANGO_SECRET_KEY": "test",
                "DJANGO_ALLOWED_HOSTS": '["juju.test"]',
                "DJANGO_METRICS_PORT": "9102",
                "DJANGO_METRICS_PATH": "/metrics",
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
            id="django",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            "fastapi",
            {
                "non-optional-string": "test",
            },
            "/bin/python3 -m uvicorn app:app",
            {
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_BASE_URL": "http://juju.test/",
                "APP_SECRET_KEY": "test",
                "APP_NON_OPTIONAL_STRING": "test",
                "APP_OIDC_CLIENT_ID": "test-client-id",
                "APP_OIDC_CLIENT_SECRET": "abc",
                "APP_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "APP_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "APP_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "APP_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "APP_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "APP_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "UVICORN_HOST": "0.0.0.0",
                "UVICORN_LOG_LEVEL": "info",
                "UVICORN_PORT": "8000",
                "METRICS_PORT": "9464",
                "METRICS_PATH": "/metrics",
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
                "PYTHONPATH": "/tmp/fastapi/log_config",
                "UVICORN_LOG_CONFIG": "/tmp/fastapi/log_config/uvicorn-log-config.json",
            },
            id="fastapi",
        ),
        pytest.param(
            "go_base_state",
            GoCharm,
            "go",
            {},
            "go-app",
            {
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_BASE_URL": "http://juju.test/",
                "APP_SECRET_KEY": "test",
                "APP_OIDC_CLIENT_ID": "test-client-id",
                "APP_OIDC_CLIENT_SECRET": "abc",
                "APP_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "APP_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "APP_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "APP_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "APP_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "APP_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "PORT": "8080",
                "METRICS_PORT": "8080",
                "METRICS_PATH": "/metrics",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/go-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "go-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/go-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="go",
        ),
        pytest.param(
            "expressjs_base_state",
            ExpressJSCharm,
            "expressjs",
            {},
            "npm start",
            {
                "APP_OIDC_REDIRECT_PATH": "/oauth/callback",
                "APP_OIDC_SCOPES": "openid profile email phone",
                "APP_BASE_URL": "http://juju.test/",
                "APP_OIDC_AUTHORIZE_URL": "https://traefik_ip/model_name-hydra/oauth2/auth",
                "APP_OIDC_ACCESS_TOKEN_URL": "https://traefik_ip/model_name-hydra/oauth2/token",
                "APP_OIDC_USER_URL": "https://traefik_ip/model_name-hydra/userinfo",
                "APP_OIDC_JWKS_URL": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
                "APP_OIDC_API_BASE_URL": "https://traefik_ip/model_name-hydra",
                "APP_OIDC_CLIENT_ID": "test-client-id",
                "APP_OIDC_CLIENT_KWARGS": '{"scope": "openid profile email phone"}',
                "APP_OIDC_CLIENT_SECRET": "abc",
                "NODE_ENV": "production",
                "APP_SECRET_KEY": "test",
                "PORT": "8080",
                "METRICS_PORT": "9464",
                "METRICS_PATH": "/metrics",
                "POSTGRESQL_DB_CONNECT_STRING": "postgresql://test-username:test-password@test-postgresql:5432/expressjs-k8s",
                "POSTGRESQL_DB_FRAGMENT": "",
                "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
                "POSTGRESQL_DB_NAME": "expressjs-k8s",
                "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
                "POSTGRESQL_DB_PARAMS": "",
                "POSTGRESQL_DB_PASSWORD": "test-password",
                "POSTGRESQL_DB_PATH": "/expressjs-k8s",
                "POSTGRESQL_DB_PORT": "5432",
                "POSTGRESQL_DB_QUERY": "",
                "POSTGRESQL_DB_SCHEME": "postgresql",
                "POSTGRESQL_DB_USERNAME": "test-username",
            },
            id="expressjs",
        ),
    ],
)
def test_oauth_config_correct_relation_order(
    base_state: dict,
    charm,
    framework: str,
    config: dict,
    command: str,
    env: dict,
    request,
    context_factory,
    charm_root,
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
    context = context_factory(charm, paas_config=_oauth_paas_config(charm_root(charm)))
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.ActiveStatus()

    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"].append(testing.Secret(id=secret_id, tracked_content={"secret": "abc"}))

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
            {},
            id="flask",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {},
            id="django",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "non-optional-string": "test",
            },
            id="fastapi",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-user-name-attribute": "email",
            },
            id="spring-boot",
        ),
        pytest.param(
            "go_base_state",
            GoCharm,
            {},
            id="go",
        ),
        pytest.param(
            "expressjs_base_state",
            ExpressJSCharm,
            {},
            id="expressjs",
        ),
    ],
)
def test_oauth_config_remove_ingress_integration_should_block(
    base_state: dict, charm, config: dict, request, context_factory, charm_root
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
    context = context_factory(charm, paas_config=_oauth_paas_config(charm_root(charm)))
    out = context.run(context.on.relation_changed(ingress_relation), state)

    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"].append(testing.Secret(id=secret_id, tracked_content={"secret": "abc"}))

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
            {},
            id="flask",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {},
            id="django",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "non-optional-string": "test",
            },
            id="fastapi",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-user-name-attribute": "email",
            },
            id="spring-boot",
        ),
        pytest.param(
            "go_base_state",
            GoCharm,
            {},
            id="go",
        ),
        pytest.param(
            "expressjs_base_state",
            ExpressJSCharm,
            {},
            id="expressjs",
        ),
    ],
)
def test_oauth_config_remove_oauth_integration_should_not_block(
    base_state: dict, charm, config: dict, request, context_factory, charm_root
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
    context = context_factory(charm, paas_config=_oauth_paas_config(charm_root(charm)))
    out = context.run(context.on.relation_changed(ingress_relation), state)

    oauth_relation = testing.Relation(
        endpoint="oidc",
        interface="oauth",
        remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"].append(testing.Secret(id=secret_id, tracked_content={"secret": "abc"}))

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
            {},
            id="flask",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {},
            id="django",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "non-optional-string": "test",
            },
            id="fastapi",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-user-name-attribute": "email",
            },
            id="spring-boot",
        ),
        pytest.param(
            "go_base_state",
            GoCharm,
            {},
            id="go",
        ),
        pytest.param(
            "expressjs_base_state",
            ExpressJSCharm,
            {},
            id="expressjs",
        ),
    ],
)
def test_blocked_when_relation_data_empty(
    base_state: dict, charm, config: dict, request, context_factory, charm_root
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
        endpoint="oidc", interface="oauth", remote_app_data={}, remote_app_name="OIDC_CHARM"
    )
    base_state["relations"].append(oauth_relation)
    base_state["secrets"].append(testing.Secret(id=secret_id, tracked_content={"secret": "abc"}))
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = context_factory(charm, paas_config=_oauth_paas_config(charm_root(charm)))
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.BlockedStatus("Please check OIDC_CHARM charm!")


@pytest.mark.parametrize(
    "base_state, charm, config, additional_oauth",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            {},
            {"framework": "flask"},
            id="flask",
        ),
        pytest.param(
            "django_base_state",
            DjangoCharm,
            {},
            {"framework": "django"},
            id="django",
        ),
        pytest.param(
            "spring_boot_base_state",
            SpringBootCharm,
            {
                "oidc-user-name-attribute": "email",
                "google-user-name-attribute": "email",
            },
            {"framework": "springboot"},
            id="spring-boot",
        ),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "non-optional-string": "test",
            },
            {"framework": "fastapi"},
            id="fastapi",
        ),
        pytest.param(
            "go_base_state",
            GoCharm,
            {},
            {"framework": "go"},
            id="go",
        ),
        pytest.param(
            "expressjs_base_state",
            ExpressJSCharm,
            {},
            {"framework": "expressjs"},
            id="expressjs",
        ),
    ],
)
def test_oauth_multiple_oauth_integrations(
    base_state: dict,
    additional_oauth: dict,
    charm,
    config: dict,
    request,
    context_factory,
    charm_root,
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
    base_state["secrets"].append(testing.Secret(id=secret_id, tracked_content={"secret": "abc"}))
    ingress_relation = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
    )
    base_state["relations"].append(ingress_relation)
    state = testing.State(**base_state)
    context = context_factory(
        charm,
        paas_config=_oauth_paas_config(charm_root(charm)),
        additional_oauth=bool(additional_oauth),
    )
    out = context.run(context.on.relation_changed(ingress_relation), state)
    assert out.unit_status == testing.BlockedStatus(
        "Multiple OAuth relations are not supported at the moment"
    )


class TestOAuthRelationConfig:
    """Tests for the OAuth settings under ``relations``."""

    def test_defaults(self):
        """Default to the /callback redirect path and the openid, profile and email scopes."""
        config = PaasConfig(relations={"oidc": {}})
        assert config.relations["oidc"] == OAuthRelationConfig(
            redirect_path="/callback", scopes=["openid", "profile", "email"]
        )

    def test_valid(self):
        """Parse the hyphenated keys used in paas-config.yaml."""
        config = PaasConfig(
            relations={"oidc": {"redirect-path": "/oauth/callback", "scopes": ["openid", "phone"]}}
        )
        assert config.relations["oidc"].redirect_path == "/oauth/callback"
        assert config.relations["oidc"].scopes == ["openid", "phone"]

    @pytest.mark.parametrize(
        "settings, diagnostic",
        [
            pytest.param(
                {"scopes": ["profile", "email"]}, "include 'openid'", id="missing-openid"
            ),
            pytest.param({"scopes": "openid profile"}, "valid list", id="scopes-as-string"),
            pytest.param({"scopes": ["openid", "a b"]}, "invalid OAuth scope", id="space"),
            pytest.param({"scopes": ["openid", ""]}, "invalid OAuth scope", id="empty-scope"),
            pytest.param({"redirect-path": ""}, "at least 1 character", id="empty-path"),
            pytest.param({"redirect_url": "/callback"}, "Extra inputs", id="unknown-key"),
        ],
    )
    def test_invalid(self, tmp_path, settings, diagnostic):
        """Reject invalid OAuth settings when reading paas-config.yaml."""
        (tmp_path / CONFIG_FILE_NAME).write_text(
            yaml.safe_dump({"relations": {"oidc": settings}}), encoding="utf-8"
        )
        with pytest.raises(PaasConfigError) as exc_info:
            read_paas_config(tmp_path)
        assert "relations.oidc" in str(exc_info.value)
        assert diagnostic in str(exc_info.value.__cause__)

    @pytest.mark.parametrize(
        "endpoint, diagnostic",
        [
            pytest.param("missing", "unknown endpoint 'missing'", id="unknown-endpoint"),
            pytest.param("postgresql", "'oauth' interface", id="non-oauth-endpoint"),
        ],
    )
    def test_invalid_endpoint(self, context_factory, endpoint, diagnostic):
        """Reject settings for endpoints that are not declared OAuth endpoints."""
        context = context_factory(FlaskCharm, paas_config=PaasConfig(relations={endpoint: {}}))
        with pytest.raises(testing.errors.UncaughtCharmError) as exc_info:
            context.run(context.on.config_changed(), testing.State())
        assert isinstance(exc_info.value.__cause__, PaasConfigError)
        assert diagnostic in str(exc_info.value.__cause__)

    @pytest.mark.parametrize(
        "base_state, charm, framework, prefix",
        [
            pytest.param("flask_base_state", FlaskCharm, "flask", "FLASK_", id="flask"),
            pytest.param("django_base_state", DjangoCharm, "django", "DJANGO_", id="django"),
            pytest.param("fastapi_base_state", FastAPICharm, "fastapi", "APP_", id="fastapi"),
            pytest.param("go_base_state", GoCharm, "go", "APP_", id="go"),
            pytest.param(
                "expressjs_base_state", ExpressJSCharm, "expressjs", "APP_", id="expressjs"
            ),
            pytest.param(
                "spring_boot_base_state", SpringBootCharm, "spring-boot", "APP_", id="spring-boot"
            ),
        ],
    )
    def test_environment_without_relation(  # pylint: disable=too-many-arguments
        self, request, context_factory, charm_root, base_state, charm, framework, prefix
    ):
        """Do not expose OAuth settings before a client is available."""
        paas_config = read_paas_config(charm_root(charm)).model_copy(
            update={
                "relations": {
                    "oidc": OAuthRelationConfig(redirect_path="/auth", scopes=["openid", "x"])
                }
            }
        )
        state = request.getfixturevalue(base_state)
        if charm is FastAPICharm:
            state["config"] = {**state.get("config", {}), "non-optional-string": "test"}
        context = context_factory(charm, paas_config=paas_config)
        out = context.run(context.on.config_changed(), testing.State(**state))
        env = list(out.containers)[0].plan.services[framework].environment
        assert f"{prefix}OIDC_REDIRECT_PATH" not in env
        assert f"{prefix}OIDC_SCOPES" not in env

    def test_defaults_when_endpoint_omitted(self, context_factory, flask_base_state):
        """Fall back to OAuthRelationConfig defaults when relations omits the OAuth endpoint."""
        secret_id = token_hex(16)
        ingress_relation = testing.Relation(
            endpoint="ingress",
            interface="ingress",
            remote_app_data={"ingress": '{"url": "http://juju.test/"}'},
        )
        oauth_relation = testing.Relation(
            endpoint="oidc",
            interface="oauth",
            remote_app_data={**OAUTH_RELATION_DATA_EXAMPLE, "client_secret_id": secret_id},
        )
        flask_base_state["relations"].extend([ingress_relation, oauth_relation])
        flask_base_state["secrets"].append(
            testing.Secret(id=secret_id, tracked_content={"secret": "abc"})
        )
        context = context_factory(FlaskCharm, paas_config=PaasConfig())
        out = context.run(
            context.on.relation_changed(ingress_relation), testing.State(**flask_base_state)
        )
        env = out.get_container("app").plan.services["flask"].environment
        assert env["FLASK_OIDC_REDIRECT_PATH"] == "/callback"
        assert env["FLASK_OIDC_SCOPES"] == "openid profile email"
        oidc_out = out.get_relation(oauth_relation.id)
        assert oidc_out.local_app_data["redirect_uri"] == "http://juju.test/callback"
        assert oidc_out.local_app_data["scope"] == "openid profile email"
