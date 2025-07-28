# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around OAuth integration lib."""
import logging

import ops
from charms.hydra.v0.oauth import ClientConfig, OAuthRequirer
from ops import ConfigData
from pydantic import BaseModel, ValidationError

from paas_charm.exceptions import CharmConfigInvalidError, InvalidRelationDataError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


class PaaSOAuthRelationData(BaseModel):
    """Configuration for accessing OAuth.

    Attributes:
        client_id: The client ID for the OAuth application.
        client_secret: The client secret for the OAuth application.
        issuer_url: The URL of the OAuth issuer.
        authorization_endpoint: The URL for the OAuth authorization endpoint.
        token_endpoint: The URL for the OAuth token endpoint.
        userinfo_endpoint: The URL for the OAuth userinfo endpoint.
        jwks_endpoint: The URL for the JSON Web Key Set (JWKS) endpoint.
        scopes: List of scopes to request during the OAuth flow.
        provider_name: The name of the OAuth identity provider.
        redirect_uri: Redirection URI to which the response will be sent.
        user_name_attribute: Claim that identifies the user in the workload system.
    """

    client_id: str
    client_secret: str
    issuer_url: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_endpoint: str
    scopes: str
    provider_name: str
    redirect_uri: str
    user_name_attribute: str


class InvalidOAuthRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid  OAuth relation data.

    Attributes:
        relation: The OAuth relation name.
    """

    relation = "oauth"


class PaaSOAuthRequirer(OAuthRequirer):
    """Wrapper around OAuthRequirer."""

    def __init__(
        self,
        charm: ops.CharmBase,
        base_url: str,
        charm_config: ConfigData,
        relation_name: str,
    ):
        """Initialize the OAuthRequirer.

        Args:
            charm: The charm instance.
            base_url: The base URL for the workload app.
            relation_name: The name of the relation.
            charm_config: The charm configuration.
        """
        self._base_url = base_url
        self._charm_config = charm_config
        super().__init__(
            charm=charm,
            client_config=self._get_oauth_client_config(relation_name),
            relation_name=relation_name,
        )

    def to_relation_data(self) -> "PaaSOAuthRelationData | None":
        """Get OAuth relation data object.

        Raises:
            InvalidOAuthRelationDataError: If invalid OAuth connection parameters were provided.

        Returns:
            Data required to integrate with OAuth.
        """
        try:
            if not self.is_client_created():
                return None
            prod_info = self.get_provider_info()
            user_name_attribute = str(
                self._charm_config.get(f"{self._relation_name}-user-name-attribute", "sub")
            )
            return PaaSOAuthRelationData.model_validate(
                {
                    "client_id": prod_info.client_id,
                    "client_secret": prod_info.client_secret,
                    "issuer_url": prod_info.issuer_url,
                    "authorization_endpoint": prod_info.authorization_endpoint,
                    "token_endpoint": prod_info.token_endpoint,
                    "userinfo_endpoint": prod_info.userinfo_endpoint,
                    "jwks_endpoint": prod_info.jwks_endpoint,
                    "scopes": self._client_config.scope,
                    "provider_name": self._relation_name,
                    "redirect_uri": self._client_config.redirect_uri,
                    "user_name_attribute": user_name_attribute,
                }
            )
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidOAuthRelationDataError(
                f"Invalid {PaaSOAuthRelationData.__name__}: {error_messages.short}"
            ) from exc

    def _get_oauth_client_config(self, relation_name: str) -> ClientConfig:
        """Get the OAuth client configuration for a given endpoint name.

        Returns:
            A ClientConfig instance with the configuration for the given endpoint.
        """
        redirect_path = str(self._charm_config.get(f"{relation_name}-redirect-path", "/callback"))
        scopes = str(self._charm_config.get(f"{relation_name}-scopes"))

        return ClientConfig(
            redirect_uri=f"{self._base_url}/{redirect_path.strip('/')}",
            scope=scopes,
            grant_types=["authorization_code"],
        )

    def update_client(self) -> None:
        """Update the OAuth client configuration.

        Raises:
            CharmConfigInvalidError: If the scope doesn't include `openid`.
        """
        config = self._get_oauth_client_config(self._relation_name)

        if "openid" not in config.scope:
            msg = "The 'openid' scope is required for OAuth integration, please add it to the scopes."
            raise CharmConfigInvalidError(msg)

        self.update_client_config(config)

    def is_related(self) -> bool:
        """Check if the charm is related to an Oauth provider charm.

        Returns:
            True if the charm is related to an Oauth provider charm.
        """
        return bool(self.model.relations.get(self._relation_name))

    def get_related_app_name(self) -> str:
        """Return the related Oauth provider charm's name.

        Returns:
            Name of the Oauth provider charm.
        """
        return self.model.relations.get(self._relation_name)[0].app.name
