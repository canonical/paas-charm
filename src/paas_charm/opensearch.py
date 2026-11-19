# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the built-in relation for the opensearch_client interface."""

from pydantic import BaseModel, Field

from paas_charm.relations import CustomRelation, OnChange

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
    # Check if opensearch-client promises to provide the value.
    # If it is, it should not be None.
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
        """

    def ensure_ready(self) -> None:
        """Check that the provider has shared the OpenSearch connection details."""

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this relation.

        Returns:
            A mapping of environment variable names to values.
        """
        return {}

    def _relation_data(self) -> PaaSOpenSearchRelationData | None:
        """Return the provider's connection details, or None until it has shared them.

        Returns:
            The provider's connection details, or None until it has shared them.
        """
        return None

    @staticmethod
    def _generate_opensearch_env(
        relation_data: PaaSOpenSearchRelationData | None,
    ) -> dict[str, str]:
        """Return the OPENSEARCH_* variables.

        Args:
            relation_data: The provider's connection details.

        Returns:
            A mapping of environment variable names to values.
        """
        return {}
