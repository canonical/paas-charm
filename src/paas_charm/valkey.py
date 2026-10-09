# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around the valkey_client interface."""

import logging

import ops
from dpcharmlibs.interfaces import (
    RequirerCommonModel,
    ResourceRequirerEventHandler,
    ValkeyResponseModel,
)
from pydantic import ValidationError

from paas_charm.app import _db_url_to_env_variables
from paas_charm.exceptions import InvalidRelationDataError
from paas_charm.relations import CustomRelation, OnChange
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

VALKEY_RELATION_NAME = "valkey"


class InvalidValkeyRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid Valkey relation data.

    Attributes:
        relation: The valkey relation name.
    """

    relation = VALKEY_RELATION_NAME


class ValkeyTLSNotSupportedError(InvalidRelationDataError):
    """Raised when Valkey TLS mode is enabled but not yet supported.

    Attributes:
        relation: The valkey relation name.
    """

    relation = VALKEY_RELATION_NAME


class ValkeyMultipleRelationsNotSupportedError(InvalidRelationDataError):
    """Raised when multiple Valkey relations are detected but not yet supported.

    Attributes:
        relation: The valkey relation name.
    """

    relation = VALKEY_RELATION_NAME


class ValkeyClientRequirer:  # pylint: disable=too-few-public-methods
    """Wrapper around ResourceRequirerEventHandler for Valkey."""

    def __init__(
        self,
        charm: ops.CharmBase,
        relation_name: str = VALKEY_RELATION_NAME,
    ) -> None:
        """Initialize the Valkey requirer.

        Args:
            charm: The charm instance.
            relation_name: The name of the relation.
        """
        self.valkey_interface = ResourceRequirerEventHandler(
            charm,
            relation_name,
            [RequirerCommonModel(resource="*")],
            response_model=ValkeyResponseModel,
        )

    def to_relation_data(self) -> ValkeyResponseModel | None:
        """Get Valkey relation data object.

        The dpcharmlibs build_model resolves secret fields (username, password)
        automatically via model validators when the repository context is provided.

        Raises:
            InvalidValkeyRelationDataError: If invalid Valkey connection parameters were provided.
            ValkeyMultipleRelationsNotSupportedError: If more than one valkey relation exists.
            ValkeyTLSNotSupportedError: If the Valkey relation has TLS enabled.

        Returns:
            ValkeyResponseModel with resolved secrets, or None if not ready.
        """
        relations = self.valkey_interface.relations
        if not relations:
            return None
        if len(relations) > 1:
            raise ValkeyMultipleRelationsNotSupportedError(
                "Multiple valkey relations are not supported"
            )
        try:
            relation = relations[0]
            model = self.valkey_interface.interface.build_model(
                relation.id, component=relation.app
            )
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidValkeyRelationDataError(
                f"Invalid ValkeyResponseModel: {error_messages.short}"
            ) from exc

        if not model.requests:
            return None
        response = model.requests[0]
        if response.tls:
            raise ValkeyTLSNotSupportedError("TLS mode is not supported for Valkey")
        return response


class ValkeyRelation(CustomRelation):
    """Valkey key-value store relation.

    Attrs:
        relation_name: Name of the relation.
    """

    relation_name = VALKEY_RELATION_NAME

    def setup(self, on_change: OnChange) -> None:
        """Wire Valkey resource-created events.

        Args:
            on_change: callback requesting a reconcile/``restart``.
        """
        requires = self.charm.framework.meta.requires
        if "valkey" not in requires or requires["valkey"].interface_name != "valkey_client":
            return

        self._requirer = ValkeyClientRequirer(
            charm=self.charm, relation_name=ValkeyRelation.relation_name
        )
        self._framework_observe(
            self._requirer.valkey_interface.on.resource_created, on_change, True
        )

    def is_ready(self) -> bool:
        """Return True when Valkey relation data is present.

        Returns:
            True if the relation is not configured or has valid data;
            False if configured but data is absent.
        """
        if not self._requirer:  # not configured
            return True
        return self._requirer.to_relation_data() is not None

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this relation.

        Called only when :meth:`is_ready` returns ``True``.

        Returns:
            A mapping of environment variable names to values (default ``{}``).
        """
        if self._requirer:
            return self._generate_valkey_env(self._requirer.to_relation_data())
        return {}

    @staticmethod
    def _generate_valkey_env(
        relation_data: ValkeyResponseModel | None = None,
    ) -> dict[str, str]:
        """Generate environment variables from Valkey relation data.

        Args:
            relation_data: The ValkeyResponseModel from dpcharmlibs with resolved secrets.

        Returns:
            Valkey environment mappings if Valkey relation data is available, empty
            dictionary otherwise.
        """
        if not relation_data:
            return {}
        endpoint = str(relation_data.endpoints)
        user_info = (
            f"{relation_data.username}:{relation_data.password}@" if relation_data.username else ""
        )
        prefix = "VALKEY"
        # Ensure the scheme in the url so that urllib can properly parse it into components.
        # Valkey sends the url without the scheme ( valkey_primary:6123 )
        # This normalizes that URL to become valkey://valkey_primary:6123
        if "://" not in endpoint:
            endpoint = f"{prefix.lower()}://{user_info}{endpoint}"
        else:
            scheme, netloc = endpoint.split("://", 1)
            endpoint = f"{scheme}://{user_info}{netloc}"

        return {
            **_db_url_to_env_variables(prefix, endpoint),
            f"{prefix}_DB_READ_ONLY_ENDPOINTS": relation_data.read_only_endpoints or "",
            f"{prefix}_DB_SENTINEL_ENDPOINTS": relation_data.sentinel_endpoints or "",
            f"{prefix}_MODE": relation_data.mode or "",
            f"{prefix}_VERSION": relation_data.version or "",
        }
