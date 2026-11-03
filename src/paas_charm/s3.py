# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around S3 integration lib."""

import json
import logging
from typing import Optional

# The import may fail if optional libs are not fetched. Let it fall through
# and let the caller (charm.py) handle it, to make this wrapper act like the
# native lib module.
from charms.data_platform_libs.v0.s3 import S3Requirer
from pydantic import BaseModel, Field, ValidationError

from paas_charm.exceptions import (
    InvalidRelationDataError,
    InvalidRelationInterfaceError,
    RelationDataError,
)
from paas_charm.relations import CustomRelation, OnChange
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

S3_RELATION_NAME = "s3"


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

    relation = S3_RELATION_NAME


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


class S3Relation(CustomRelation):
    """S3 object storage relation.

    Attrs:
        relation_name: Name of the relation.
    """

    relation_name = S3_RELATION_NAME

    def setup(self, on_change: OnChange) -> None:
        """Wire S3 credentials events.

        Args:
            on_change: callback requesting a reconcile/``restart``.

        Raises:
            InvalidRelationInterfaceError: If the built-in S3 relation uses an invalid
                interface.
        """
        requires = self.charm.framework.meta.requires
        if requires[S3_RELATION_NAME].interface_name != "s3":
            raise InvalidRelationInterfaceError("Built-in S3 relation interface is not 's3'")

        self._requirer = PaaSS3Requirer(
            charm=self.charm,
            relation_name=S3Relation.relation_name,
            bucket_name=self.context.app_name,
        )
        self._framework_observe(self._requirer.on.credentials_changed, on_change, True)
        self._framework_observe(self._requirer.on.credentials_gone, on_change, False)

    def ensure_ready(self) -> None:
        """Check that configured S3 relation data is ready.

        Raises:
            RelationDataError: If configured S3 relation data is absent or invalid.
        """
        if not self._requirer:  # not configured
            return
        try:
            relation_data = self._requirer.to_relation_data()
        except InvalidRelationDataError as exc:
            raise RelationDataError(str(exc), self.relation_name) from exc
        if relation_data is None:
            raise RelationDataError("S3 relation data is not ready", self.relation_name)

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this relation.

        Returns:
            A mapping of environment variable names to values (default ``{}``).
        """
        if self._requirer:
            return self._generate_s3_env(self._requirer.to_relation_data())
        return {}

    @staticmethod
    def _generate_s3_env(relation_data: PaaSS3RelationData | None = None) -> dict[str, str]:
        """Generate environment variables from S3 relation data.

        Args:
            relation_data: The charm S3 integration relation data.

        Returns:
            Default S3 environment mappings if relation data is available, empty
            dictionary otherwise.
        """
        if not relation_data:
            return {}
        return {
            k: v
            for k, v in (
                ("S3_ACCESS_KEY", relation_data.access_key),
                ("S3_SECRET_KEY", relation_data.secret_key),
                ("S3_REGION", relation_data.region),
                ("S3_STORAGE_CLASS", relation_data.storage_class),
                ("S3_BUCKET", relation_data.bucket),
                ("S3_ENDPOINT", relation_data.endpoint),
                ("S3_PATH", relation_data.path),
                ("S3_API_VERSION", relation_data.s3_api_version),
                ("S3_URI_STYLE", relation_data.s3_uri_style),
                ("S3_ADDRESSING_STYLE", relation_data.addressing_style),
                (
                    "S3_ATTRIBUTES",
                    json.dumps(relation_data.attributes) if relation_data.attributes else None,
                ),
                (
                    "S3_TLS_CA_CHAIN",
                    json.dumps(relation_data.tls_ca_chain) if relation_data.attributes else None,
                ),
            )
            if v is not None
        }
