# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the SMTP relation for the custom relations framework."""

import logging

from charmlibs.interfaces.smtp import SecretError, SmtpRelationData, SmtpRequires
from pydantic import ValidationError

from paas_charm.exceptions import (
    InvalidRelationDataError,
    InvalidRelationInterfaceError,
    RelationDataError,
)
from paas_charm.relations import CustomRelation, OnChange
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

SMTP_RELATION_NAME = "smtp"


class InvalidSmtpRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid SMTP relation data.

    Attributes:
        relation: The SMTP relation name.
    """

    relation = SMTP_RELATION_NAME


class SmtpRelation(CustomRelation):
    """SMTP relation.

    Attrs:
        relation_name: Name of the relation.
    """

    relation_name = SMTP_RELATION_NAME

    def setup(self, on_change: OnChange) -> None:
        """Wire SMTP data events.

        Args:
            on_change: callback requesting a reconcile/``restart``.

        Raises:
            InvalidRelationInterfaceError: If the built-in SMTP relation uses an invalid
                interface.
        """
        requires = self.charm.framework.meta.requires
        if requires[SMTP_RELATION_NAME].interface_name != "smtp":
            raise InvalidRelationInterfaceError("Built-in SMTP relation interface is not 'smtp'")

        self._requirer = SmtpRequires(self.charm, relation_name=SmtpRelation.relation_name)
        self._framework_observe(self._requirer.on.smtp_data_available, on_change)

    def _to_relation_data(self) -> SmtpRelationData | None:
        """Get the SMTP relation data, translating invalid data errors.

        Raises:
            InvalidSmtpRelationDataError: If the SMTP relation data is invalid.

        Returns:
            The SMTP relation data, or None if not configured or not available.
        """
        if not self._requirer:
            return None
        try:
            return self._requirer.get_relation_data()
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidSmtpRelationDataError(
                f"Invalid {SmtpRelationData.__name__}: {error_messages.short}"
            ) from exc
        except (SecretError, ValueError, TypeError) as exc:
            logger.error("Invalid SMTP relation data: %s", exc)
            raise InvalidSmtpRelationDataError(f"Invalid SMTP relation data: {exc}") from exc

    def get_relation_data(self) -> SmtpRelationData | None:
        """Get the SMTP relation data.

        Returns:
            The SMTP relation data, or None if not configured, not available or invalid.
        """
        try:
            return self._to_relation_data()
        except InvalidSmtpRelationDataError:
            return None

    def ensure_ready(self) -> None:
        """Check that configured SMTP relation data is ready.

        Raises:
            RelationDataError: If configured SMTP relation data is absent or invalid.
        """
        if not self._requirer:  # not configured
            return
        try:
            relation_data = self._to_relation_data()
        except InvalidRelationDataError as exc:
            raise RelationDataError(str(exc), self.relation_name) from exc
        if relation_data is None:
            raise RelationDataError("SMTP relation data is not ready", self.relation_name)

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this relation.

        Returns:
            A mapping of environment variable names to values (default ``{}``).
        """
        return self._generate_smtp_env(self.get_relation_data())

    @staticmethod
    def _generate_smtp_env(relation_data: SmtpRelationData | None = None) -> dict[str, str]:
        """Generate environment variables from SMTP relation data.

        Args:
            relation_data: The charm SMTP integration relation data.

        Returns:
            SMTP environment mappings if SMTP relation data is available, empty
            dictionary otherwise.
        """
        if not relation_data:
            return {}
        return {
            k: v
            for k, v in (
                ("SMTP_HOST", relation_data.host),
                ("SMTP_PORT", str(relation_data.port)),
                ("SMTP_USER", relation_data.user),
                ("SMTP_PASSWORD", relation_data.password),
                ("SMTP_AUTH_TYPE", relation_data.auth_type.value),
                ("SMTP_TRANSPORT_SECURITY", relation_data.transport_security.value),
                ("SMTP_DOMAIN", relation_data.domain),
                ("SMTP_SKIP_SSL_VERIFY", str(relation_data.skip_ssl_verify)),
            )
            if v is not None and v not in ("", "none")
        }
