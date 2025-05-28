# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around SAML integration lib."""
import logging
import re

from charms.redis_k8s.v0.redis import RedisRequires
from pydantic import AnyUrl, BaseModel, ValidationError

from paas_charm.exceptions import InvalidRelationDataError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


class PaaSRedisRelationData(BaseModel):
    """Configuration for accessing SAML.

    Attributes:
        url: The connection URL to Redis instance.
    """

    # We don't use Pydantic provided RedisDsn because it defaults the path to /0 database which
    # is not desired. Overriding the settings otherwise require custom Pydantic data schemas.
    url: AnyUrl


class InvalidRedisRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid Redis relation data.

    Attributes:
        relation: The redis relation name.
    """

    relation = "redis"


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
            # Workaround as the Redis library temporarily sends the port
            # as None while the integration is being created.
            if not self.url or re.fullmatch(r"redis://[^:/]+:None", self.url):
                return None
            return PaaSRedisRelationData(url=self.url)
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidRedisRelationDataError(
                f"Invalid {PaaSRedisRelationData.__name__}: {error_messages.short}"
            ) from exc
