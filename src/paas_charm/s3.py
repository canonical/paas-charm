# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around S3 integration lib."""
import logging
from typing import Optional

# The import may fail if optional libs are not fetched. Let it fall through
# and let the caller (charm.py) handle it, to make this wrapper act like the
# native lib module.
from charms.data_platform_libs.v0.s3 import S3Requirer
from pydantic import BaseModel, Field, ValidationError

from paas_charm.exceptions import InvalidRelationDataError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


class PaaSS3RelationData(BaseModel):
    """Configuration for accessing S3 bucket.

    Attributes:
        access_key: AWS access key.
        secret_key: AWS secret key.
        region: The region to connect to the object storage.
        storage_class: Storage Class for objects uploaded to the object storage.
        bucket: The bucket name.
        endpoint: The endpoint used to connect to the object storage.
        path: The path inside the bucket to store objects.
        s3_api_version: S3 protocol specific API signature.
        s3_uri_style: The S3 protocol specific bucket path lookup type. Can be "path" or "host".
        addressing_style: S3 protocol addressing style, can be "path" or "virtual".
        attributes: The custom metadata (HTTP headers).
        tls_ca_chain: The complete CA chain, which can be used for HTTPS validation.
    """

    access_key: str = Field(alias="access-key")
    secret_key: str = Field(alias="secret-key")
    region: Optional[str] = None
    storage_class: Optional[str] = Field(alias="storage-class", default=None)
    bucket: str
    endpoint: Optional[str] = None
    path: Optional[str] = None
    s3_api_version: Optional[str] = Field(alias="s3-api-version", default=None)
    s3_uri_style: Optional[str] = Field(alias="s3-uri-style", default=None)
    tls_ca_chain: Optional[list[str]] = Field(alias="tls-ca-chain", default=None)
    attributes: Optional[list[str]] = None

    @property
    def addressing_style(self) -> Optional[str]:
        """Translates s3_uri_style to AWS addressing_style."""
        if self.s3_uri_style == "host":
            return "virtual"
        # If None or "path", it does not change.
        return self.s3_uri_style


class InvalidS3RelationDataError(InvalidRelationDataError):
    """Represents an error with invalid S3 relation data.

    Attributes:
        relation: The S3 relation name.
    """

    relation = "s3"


class PaaSS3Requirer(S3Requirer):
    """Wrapper around S3Requirer."""

    def to_relation_data(self) -> PaaSS3RelationData | None:
        """Get S3 relation data object.

        Raises:
            InvalidS3RelationDataError: If invalid S3 connection parameters were provided.

        Returns:
            Data required to connect to S3.
        """
        connection_info = self.get_s3_connection_info()
        if not connection_info:
            return None
        try:
            return PaaSS3RelationData.model_validate(connection_info)
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidS3RelationDataError(
                f"Invalid {PaaSS3RelationData.__name__}: {error_messages.short}"
            ) from exc
