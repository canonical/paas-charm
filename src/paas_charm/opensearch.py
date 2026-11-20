# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the built-in relation for the opensearch_client interface."""

import logging

import ops
from charms.data_platform_libs.v0.data_interfaces import OpenSearchRequires
from pydantic import BaseModel, Field, ValidationError

from paas_charm.exceptions import (
    InvalidRelationInterfaceError,
    PaasConfigError,
    RelationDataError,
)
from paas_charm.paas_config import CONFIG_FILE_NAME, read_paas_config
from paas_charm.relations import CustomRelation, OnChange

logger = logging.getLogger(__name__)

OPENSEARCH_RELATION_NAME = "opensearch"


class PaaSOpenSearchRelationData(BaseModel):
    """Connection details shared by the OpenSearch provider.

    Attributes:
        endpoints: Comma-separated list of ``host:port`` addresses of the OpenSearch nodes.
        username: Username of the user that the provider created for the relation.
        password: Password of the user that the provider created for the relation.
        index: Index that the provider created for the relation.
        version: OpenSearch version.
        tls_ca: PEM-encoded CA chain of the OpenSearch certificates.
    """

    endpoints: str
    username: str
    password: str
    tls_ca: str = Field(alias="tls-ca")
    index: str | None = None
    version: str | None = None


class OpenSearchRelation(CustomRelation):
    """The built-in opensearch relation, configured in paas-config.yaml.

    Attrs:
        relation_name: Name of the relation.
    """

    relation_name = OPENSEARCH_RELATION_NAME

    def setup(self, on_change: OnChange) -> None:
        """Create the OpenSearch requirer and wire its events to ``on_change``.

        Args:
            on_change: callback requesting a reconcile/``restart``.

        Raises:
            InvalidRelationInterfaceError: If the built-in OpenSearch relation uses an invalid
                interface.
            PaasConfigError: If paas-config.yaml has no opensearch section.
        """
        requires = self.charm.framework.meta.requires
        if requires[OPENSEARCH_RELATION_NAME].interface_name != "opensearch_client":
            raise InvalidRelationInterfaceError(
                "Built-in OpenSearch relation interface is not 'opensearch_client'"
            )
        config = read_paas_config().opensearch
        if config is None:
            raise PaasConfigError(
                f"{CONFIG_FILE_NAME} has no opensearch section, which the "
                f"{OPENSEARCH_RELATION_NAME} relation requires"
            )

        self._requirer = OpenSearchRequires(
            self.charm,
            OPENSEARCH_RELATION_NAME,
            config.index,
            extra_user_roles=config.extra_user_roles,
        )
        self._framework_observe(self._requirer.on.index_created, on_change, True)
        # OpenSearchRequires emits no event when the provider shares the CA after the
        # credentials and the endpoints, so reconcile on every relation-changed event.
        for event in (
            self._requirer.on.authentication_updated,
            self.charm.on[OPENSEARCH_RELATION_NAME].relation_changed,
            self.charm.on[OPENSEARCH_RELATION_NAME].relation_broken,
        ):
            self._framework_observe(event, on_change)

    def ensure_ready(self) -> None:
        """Check that the provider has shared the OpenSearch connection details.

        Raises:
            RelationDataError: If there is more than one opensearch relation, or if the
                connection details are missing, incomplete or unreadable.
        """
        if self._relation_data() is None:
            raise RelationDataError("OpenSearch relation data is not ready", self.relation_name)

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this relation.

        Returns:
            A mapping of environment variable names to values.
        """
        return self._generate_opensearch_env(self._relation_data())

    def _relation_data(self) -> PaaSOpenSearchRelationData | None:
        """Return the provider's connection details, or None until it has shared them.

        Raises:
            RelationDataError: If there is more than one opensearch relation, or if the
                relation secrets can't be read.

        Returns:
            The provider's connection details, or None until it has shared them.
        """
        if not self._requirer:
            return None
        relations = self._requirer.relations
        if len(relations) > 1:
            raise RelationDataError(
                "Multiple OpenSearch relations are not supported", self.relation_name
            )
        if not relations:
            return None
        try:
            databag = self._requirer.fetch_relation_data(
                fields=["endpoints", "username", "password", "tls-ca", "index", "version"]
            ).get(relations[0].id, {})
        except ops.ModelError as exc:
            logger.error("Cannot read the OpenSearch relation secrets: %s", exc)
            raise RelationDataError(
                "Cannot read the OpenSearch relation secrets", self.relation_name
            ) from exc
        try:
            return PaaSOpenSearchRelationData.model_validate(databag)
        except ValidationError:
            return None

    @staticmethod
    def _generate_opensearch_env(
        relation_data: PaaSOpenSearchRelationData | None,
    ) -> dict[str, str]:
        """Return the OPENSEARCH_* variables.

        Args:
            relation_data: The provider's connection details.

        Returns:
            A mapping of environment variable names to values, without the fields that the
            provider hasn't shared.
        """
        if not relation_data:
            return {}
        return {
            k: v
            for k, v in (
                ("OPENSEARCH_ENDPOINTS", relation_data.endpoints),
                ("OPENSEARCH_USERNAME", relation_data.username),
                ("OPENSEARCH_PASSWORD", relation_data.password),
                ("OPENSEARCH_INDEX", relation_data.index),
                ("OPENSEARCH_VERSION", relation_data.version),
                ("OPENSEARCH_TLS_CA", relation_data.tls_ca),
            )
            if v is not None
        }
