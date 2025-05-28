# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around Tempo integration lib."""
import logging

from charms.tempo_coordinator_k8s.v0.tracing import (
    ProtocolNotRequestedError,
    TracingEndpointRequirer,
)
from pydantic import AnyUrl, BaseModel, ValidationError

from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)


class PaaSTracingRelationData(BaseModel):
    """Relation data required to connect to Tempo tracing service.

    Attributes:
        endpoint: Tempo endpoint URL to send the traces.
        service_name: Tempo service name for the workload.
    """

    endpoint: AnyUrl
    service_name: str


class InvalidTracingRelationDataError(Exception):
    """Represents an error with invalid Tempo relation data.

    Attributes:
        relation: The tracing relation name.
    """

    relation = "tracing"


class PaaSTracingEndpointRequirer(TracingEndpointRequirer):
    """Wrapper around TracingEndpointRequirer to provide relation data Pydantic object."""

    def to_relation_data(self) -> PaaSTracingRelationData | None:
        """Get Tempo relation data object.

        Raises:
            InvalidTracingRelationDataError: If invalid Tempo connection parameters were provided.

        Returns:
            Data required to start Tempo tracing.
        """
        if not self.is_ready():
            return None
        try:
            endpoint = self.get_endpoint(protocol="otlp_http")
        except ProtocolNotRequestedError as exc:
            raise InvalidTracingRelationDataError(
                f"Invalid {PaaSTracingRelationData.__name__}"
            ) from exc
        if not endpoint:
            return None
        try:
            return PaaSTracingRelationData(endpoint=endpoint, service_name=self._charm.app.name)
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidTracingRelationDataError(
                f"Invalid {PaaSTracingRelationData.__name__}: {error_messages.short}"
            ) from exc
