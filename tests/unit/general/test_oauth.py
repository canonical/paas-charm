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

from examples.flask.charm.src.charm import FlaskCharm
from paas_charm.utils import config_metadata


@pytest.mark.parametrize(
    "base_state, charm, framework, config, command, env",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            "flask",
            {
                "oidc_redirect_path": "/oauth/callback",
                "oidc_scopes": "openid profile email phone",
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
                "oidc_redirect_path": "/oauth/callback",
                "oidc_scopes": "openid profile email phone",
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
                "oidc_redirect_path": "/oauth/callback",
                "oidc_scopes": "openid profile email phone",
            },
            id="flask-oidc",
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
                "oidc_redirect_path": "/oauth/callback",
                "oidc_scopes": "openid profile email phone",
            },
            id="flask-oidc",
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
                "oidc_redirect_path": "/oauth/callback",
                "oidc_scopes": "profile email phone",
            },
            id="flask-oidc-fail",
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
    "base_state, charm, config, multiple_oauth_integrations",
    [
        pytest.param(
            "flask_base_state",
            FlaskCharm,
            {
                "oidc_redirect_path": "/oauth/callback",
                "oidc_scopes": "openid profile email phone",
                "google_redirect_path": "/oauth/callback",
                "google_scopes": "openid profile email phone",
            },
            {"framework": "flask"},
            id="flask-oidc-fail",
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
