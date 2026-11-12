# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around SAML integration lib."""

import logging

# The import may fail if optional libs are not fetched. Let it fall through
# and let the caller (charm.py) handle it, to make this wrapper act like the
# native lib module.
from charms.saml_integrator.v0.saml import SamlRelationData, SamlRequires
from pydantic import ValidationError, ValidationInfo, field_validator

from paas_charm.exceptions import (
    InvalidRelationDataError,
    InvalidRelationInterfaceError,
    RelationDataError,
)
from paas_charm.relations import CustomRelation, OnChange
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

SAML_RELATION_NAME = "saml"


class PaaSSAMLRelationData(SamlRelationData):
    """Configuration for accessing SAML.

    Attributes:
        signing_certificate: Signing certificate for the SP.
        single_sign_on_redirect_url: Sign on redirect URL for the SP.
    """

    @field_validator("certificates")
    @classmethod
    def validate_signing_certificate_exists(
        cls, certs: tuple[str, ...], _: ValidationInfo
    ) -> tuple[str, ...]:
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
        if not certs:
            raise ValueError("Missing x509certs. There should be at least one certificate.")
        return certs

    @property
    def signing_certificate(self) -> str:
        """Signing certificate for the SP."""
        return self.certificates[0]

    @property
    def single_sign_on_redirect_url(self) -> str | None:
        """Sign on redirect URL for the SP."""
        for endpoint in self.endpoints:
            if (
                endpoint.name == "SingleSignOnService"
                and endpoint.url
                and "redirect" in endpoint.binding.lower()
            ):
                return str(endpoint.url)
        return None


class InvalidSAMLRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid SAML relation data.

    Attributes:
        relation: The SAML relation name.
    """

    relation = SAML_RELATION_NAME


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


class SamlRelation(CustomRelation):
    """SAML relation.

    Attrs:
        relation_name: Name of the relation.
    """

    relation_name = SAML_RELATION_NAME

    def setup(self, on_change: OnChange) -> None:
        """Wire SAML data events.

        Args:
            on_change: callback requesting a reconcile/``restart``.

        Raises:
            InvalidRelationInterfaceError: If the built-in SAML relation uses an invalid
                interface.
        """
        requires = self.charm.framework.meta.requires
        if requires[SAML_RELATION_NAME].interface_name != "saml":
            raise InvalidRelationInterfaceError("Built-in SAML relation interface is not 'saml'")

        self._requirer = PaaSSAMLRequirer(self.charm, relation_name=SamlRelation.relation_name)
        self._framework_observe(self._requirer.on.saml_data_available, on_change, True)

    def get_relation_data(self) -> PaaSSAMLRelationData | None:
        """Get the SAML relation data.

        Returns:
            The SAML relation data, or None if not configured or not available.
        """
        if not self._requirer:
            return None
        return self._requirer.to_relation_data()

    def ensure_ready(self) -> None:
        """Check that configured SAML relation data is ready.

        Raises:
            RelationDataError: If configured SAML relation data is absent or invalid.
        """
        if not self._requirer:  # not configured
            return
        try:
            relation_data = self._requirer.to_relation_data()
        except InvalidRelationDataError as exc:
            raise RelationDataError(str(exc), self.relation_name) from exc
        if relation_data is None:
            raise RelationDataError("SAML relation data is not ready", self.relation_name)

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this relation.

        Returns:
            A mapping of environment variable names to values (default ``{}``).
        """
        return self._generate_saml_env(self.get_relation_data())

    @staticmethod
    def _generate_saml_env(relation_data: PaaSSAMLRelationData | None = None) -> dict[str, str]:
        """Generate environment variables from SAML relation data.

        Args:
            relation_data: The charm SAML integration relation data.

        Returns:
            SAML environment mappings if SAML relation data is available, empty
            dictionary otherwise.
        """
        if not relation_data:
            return {}
        return {
            k: v
            for (k, v) in (
                ("SAML_ENTITY_ID", relation_data.entity_id),
                (
                    "SAML_METADATA_URL",
                    str(relation_data.metadata_url) if relation_data.metadata_url else None,
                ),
                (
                    "SAML_SINGLE_SIGN_ON_REDIRECT_URL",
                    relation_data.single_sign_on_redirect_url,
                ),
                ("SAML_SIGNING_CERTIFICATE", relation_data.signing_certificate),
            )
            if v is not None
        }
