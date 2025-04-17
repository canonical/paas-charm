# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around SAML integration lib."""
import logging

# The import may fail if optional libs are not fetched. Let it fall through
# and let the caller (charm.py) handle it, to make this wrapper act like the
# native lib module.
from charms.saml_integrator.v0.saml import SamlRelationData, SamlRequires
from pydantic import ValidationError, ValidationInfo, field_validator

from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


class PaaSSAMLRelationData(SamlRelationData):
    """Configuration for accessing SAML.

    Attributes:
        entity_id: Entity Id of the SP.
        metadata_url: URL for the metadata for the SP.
        signing_certificate: Signing certificate for the SP.
        single_sign_on_redirect_url: Sign on redirect URL for the SP.
    """

    entity_id: str
    metadata_url: str

    @property
    def signing_certificate(self) -> str:
        """Signing certificate for the SP."""
        return ",".join(self.certificates)

    @property
    def single_sign_on_redirect_url(self) -> str | None:
        """Sign on redirect URL for the SP."""
        for endpoint in self.endpoints:
            if endpoint.name == "single_sign_on_service_redirect_url" and endpoint.url:
                return str(endpoint.url)
        return None

    @field_validator("signing_certificate")
    @classmethod
    def validate_signing_certificate_exists(cls, certs: str, _: ValidationInfo) -> str:
        """Validate that at least a certificate exists in the list of certificates.

        It is a prerequisite that the fist certificate is the signing certificate,
        otherwise this method would return a wrong certificate.

        Args:
            certs: Original x509certs field

        Returns:
            The validated signing certificate

        Raises:
            ValueError: If there is no certificate.
        """
        certificate = certs.split(",")[0]
        if not certificate:
            raise ValueError("Missing x509certs. There should be at least one certificate.")
        return certificate


class PaaSSAMLRequirer(SamlRequires):
    """Wrapper around S3Requirer."""

    def to_relation_data(self) -> "PaaSSAMLRelationData | None":
        """Get SAML relation data object.

        Raises:
            CharmConfigInvalidError: If invalid SAML connection parameters were provided.

        Returns:
            Data required to integrate with SAML.
        """
        saml_data = self.get_relation_data()
        if not saml_data:
            return None
        try:
            # We need to dump and reload the PaaSSAMLRelationData since there's no way
            # to inherit it from parent SamlRelationData.
            return PaaSSAMLRelationData.model_validate(**saml_data.model_dump())
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise CharmConfigInvalidError(
                f"Invalid {PaaSSAMLRelationData.__name__}: {error_messages.short}"
            ) from exc
