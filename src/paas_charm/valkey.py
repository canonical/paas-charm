# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around the valkey_client interface."""

from dataclasses import dataclass
import logging
import typing

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


@dataclass
class ValkeyClientRelationAppData:
    """Represents the data provided by the Valkey relation provider
    after fetching secret values for username as password.
    """

    valkey_client_response: ValkeyResponseModel
    username: str
    password: str


class InvalidValkeyRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid Valkey relation data.

    Attributes:
        relation: The valkey relation name.
    """

    relation = VALKEY_RELATION_NAME


class ValkeyClientRequirer:
    """Wrapper around ResourceRequirerEventHandler for Valkey."""

    get_secret_callback: typing.Callable[[str], ops.Secret | None]

    def __init__(
        self,
        charm: ops.CharmBase,
        get_secret_callback: typing.Callable[[str], ops.Secret | None],
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
        self.get_secret_callback = get_secret_callback

    def to_relation_data(self) -> ValkeyClientRelationAppData | None:
        """Get Valkey relation data object.

        Raises:
            InvalidValkeyRelationDataError: If invalid Valkey connection parameters were provided.

        Returns:
            Data required to integrate with Valkey, or None if not ready.
        """
        try:
            if len(self.valkey_interface.relations) == 1:
                relation = self.valkey_interface.relations[0]
                valkey_client_response = relation.load(ValkeyResponseModel, relation.app)
                username = None
                if (username_secret_id := valkey_client_response.username) and (
                    secret := self.get_secret_callback(username_secret_id)
                ):
                    username = secret.get_content(refresh=True)["username"]
                password = None
                if (password_secret_id := valkey_client_response.password) and (
                    secret := self.get_secret_callback(password_secret_id)
                ):
                    password = secret.get_content(refresh=True)["password"]
                return ValkeyClientRelationAppData(
                    valkey_client_response=valkey_client_response,
                    username=username or "",
                    password=password or "",
                )
            return None
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidValkeyRelationDataError(
                f"Invalid {ValkeyClientRelationAppData.__name__}: {error_messages.short}"
            ) from exc
        except (ops.SecretNotFoundError, ops.ModelError) as exc:
            logger.error("Failed to retrieve username/password for Valkey relation: %s", exc)
            raise InvalidValkeyRelationDataError(
                f"Failed to retrieve username/password for {ValkeyClientRelationAppData.__name__}"
            ) from exc
