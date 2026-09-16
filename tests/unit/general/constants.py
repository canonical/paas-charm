# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Constants shared by General unit tests."""

OAUTH_RELATION_DATA_EXAMPLE = {
    "authorization_endpoint": "https://traefik_ip/model_name-hydra/oauth2/auth",
    "introspection_endpoint": "http://hydra.model_name.svc.cluster.local:4445/admin/oauth2/introspect",
    "issuer_url": "https://traefik_ip/model_name-hydra",
    "jwks_endpoint": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
    "scope": "openid profile email",
    "token_endpoint": "https://traefik_ip/model_name-hydra/oauth2/token",
    "userinfo_endpoint": "https://traefik_ip/model_name-hydra/userinfo",
    "client_id": "test-client-id",
}
