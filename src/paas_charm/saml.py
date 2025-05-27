# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around SAML integration lib."""
import logging

# The import may fail if optional libs are not fetched. Let it fall through
# and let the caller (charm.py) handle it, to make this wrapper act like the
# native lib module.
from charms.saml_integrator.v0.saml import SamlRelationData, SamlRequires
from pydantic import ValidationError

from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


class PaaSSAMLRelationData(SamlRelationData):
    """Configuration for accessing SAML.

    Attributes:
        signing_certificate: Signing certificate for the SP.
        single_sign_on_redirect_url: Sign on redirect URL for the SP.
    """

    @property
    def signing_certificate(self) -> str:
        """Signing certificate for the SP."""
        return ",".join(self.certificates)

    @property
    def single_sign_on_redirect_url(self) -> str | None:
        """Sign on redirect URL for the SP."""
        logger.info(
            "[DEBUG]ENDPOINTS: %s",
            list(
                (endpoint.name, endpoint.url, endpoint.response_url, endpoint.binding)
                for endpoint in self.endpoints
            ),
        )
        for endpoint in self.endpoints:
            if endpoint.name == "single_sign_on_service_redirect_url" and endpoint.url:
                return str(endpoint.url)
        return None


class InvalidSAMLRelationDataError(Exception):
    """Represents an error with invalid SAML relation data."""


class PaaSSAMLRequirer(SamlRequires):
    """Wrapper around S3Requirer."""

    def to_relation_data(self) -> "PaaSSAMLRelationData | None":
        """Get SAML relation data object.

        Raises:
            InvalidSAMLRelationDataError: If invalid SAML connection parameters were provided.

        Returns:
            Data required to integrate with SAML.
        """
        try:
            saml_data = self.get_relation_data()
            if not saml_data:
                return None
            # We need to dump and reload the PaaSSAMLRelationData since there's no way
            # to inherit it from parent SamlRelationData.
            return PaaSSAMLRelationData(
                entity_id=saml_data.entity_id,
                metadata_url=saml_data.metadata_url,
                certificates=saml_data.certificates,
                endpoints=saml_data.endpoints,
            )
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidSAMLRelationDataError(
                f"Invalid {PaaSSAMLRelationData.__name__}: {error_messages.short}"
            ) from exc
