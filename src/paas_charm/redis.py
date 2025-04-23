# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around SAML integration lib."""
import logging

from charms.redis_k8s.v0.redis import RedisRequires
from pydantic import BaseModel, RedisDsn, ValidationError

from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


# # Override RedisDsn because it defaults the path to /0 database which is not
# # desired.
PaaSRedisDsn = RedisDsn
# trying this
PaaSRedisDsn._constraints.default_path = ""  # pylint: disable=protected-access


class PaaSRedisRelationData(BaseModel):
    """Configuration for accessing SAML.

    Attributes:
        url: The connection URL to Redis instance.
    """

    url: PaaSRedisDsn


class InvalidRedisRelationDataError(Exception):
    """Represents an error with invalid Redis relation data."""


class PaaSRedisRequires(RedisRequires):
    """Wrapper around RedisRequires."""

    def to_relation_data(self) -> "PaaSRedisRelationData | None":
        """Get SAML relation data object.

        Raises:
            InvalidRedisRelationDataError: If invalid SAML connection parameters were provided.

        Returns:
            Data required to integrate with SAML.
        """
        try:
            if not self.url:
                return None
            return PaaSRedisRelationData(url=self.url)
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidRedisRelationDataError(
                f"Invalid {PaaSRedisRelationData.__name__}: {error_messages.short}"
            ) from exc
