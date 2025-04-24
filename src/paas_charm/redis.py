# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around SAML integration lib."""
import logging

from charms.redis_k8s.v0.redis import RedisRequires
from pydantic import AnyUrl, BaseModel, Field, UrlConstraints, ValidationError

from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


# Pydantic provided RedisDsn because it defaults the path to /0 database which
# is not desired.
class PaaSRedisDsn(AnyUrl):
    """A type that will accept any Redis DSN.

    * User info required
    * TLD not required
    * Host required (e.g., `rediss://:pass@localhost`)
    """

    _constraints = UrlConstraints(
        allowed_schemes=["redis", "rediss"],
        default_host="localhost",
        default_port=6379,
        default_path="",
        host_required=True,
    )

    @property
    def host(self) -> str:
        """The required URL host."""
        return self._url.host  # pyright: ignore[reportReturnType]


class PaaSRedisRelationData(BaseModel):
    """Configuration for accessing SAML.

    Attributes:
        url: The connection URL to Redis instance.
    """

    url: PaaSRedisDsn = Field()


class InvalidRedisRelationDataError(Exception):
    """Represents an error with invalid Redis relation data."""


class PaaSRedisRequires(RedisRequires):
    """Wrapper around RedisRequires."""

    def to_relation_data(self) -> "PaaSRedisRelationData | None":
        """Get SAML relation data object.

        Raises:
            InvalidSAMLRelationDataError: If invalid SAML connection parameters were provided.

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
