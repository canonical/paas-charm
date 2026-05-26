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

from paas_charm.exceptions import InvalidRelationDataError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

VALKEY_RELATION_NAME = "valkey"


class InvalidValkeyRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid Valkey relation data.

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

        Returns:
            ValkeyResponseModel with resolved secrets, or None if not ready.
        """
        try:
            if len(self.valkey_interface.relations) == 1:
                relation = self.valkey_interface.relations[0]
                model = self.valkey_interface.interface.build_model(
                    relation.id, component=relation.app
                )
                if not model.requests:
                    return None
                return model.requests[0]
            return None
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidValkeyRelationDataError(
                f"Invalid ValkeyResponseModel: {error_messages.short}"
            ) from exc
