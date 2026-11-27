# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide a wrapper around Tempo integration lib."""

import logging
import urllib.parse

from charmlibs.interfaces.tracing import (
    ProtocolNotRequestedError,
    TracingEndpointRequirer,
)
from pydantic import AnyUrl, BaseModel, ValidationError

from paas_charm.exceptions import (
    InvalidRelationDataError,
    InvalidRelationInterfaceError,
    RelationDataError,
)
from paas_charm.relations import CustomRelation, OnChange
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

TRACING_RELATION_NAME = "tracing"


class PaaSTracingRelationData(BaseModel):
    """Relation data required to connect to Tempo tracing service.

    Attributes:
        endpoint: Tempo endpoint URL to send the traces.
        service_name: Tempo service name for the workload.
    """

    endpoint: AnyUrl
    service_name: str


class InvalidTracingRelationDataError(InvalidRelationDataError):
    """Represents an error with invalid Tempo relation data.

    Attributes:
        relation: The tracing relation name.
    """

    relation = TRACING_RELATION_NAME


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
            return PaaSTracingRelationData.model_validate(
                {"endpoint": endpoint, "service_name": self._charm.app.name}
            )
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise InvalidTracingRelationDataError(
                f"Invalid {PaaSTracingRelationData.__name__}: {error_messages.short}"
            ) from exc


class TracingRelation(CustomRelation):
    """Tempo tracing relation.

    Attrs:
        relation_name: Name of the relation.
    """

    relation_name = TRACING_RELATION_NAME

    def setup(self, on_change: OnChange) -> None:
        """Wire tracing endpoint events.

        Args:
            on_change: callback requesting a reconcile/``restart``.

        Raises:
            InvalidRelationInterfaceError: If the built-in tracing relation uses an invalid
                interface.
        """
        requires = self.charm.framework.meta.requires
        if requires[TRACING_RELATION_NAME].interface_name != "tracing":
            raise InvalidRelationInterfaceError(
                "Built-in tracing relation interface is not 'tracing'"
            )

        self._requirer = PaaSTracingEndpointRequirer(
            self.charm,
            relation_name=TracingRelation.relation_name,
            protocols=["otlp_http"],
        )
        self._framework_observe(self._requirer.on.endpoint_changed, on_change)
        self._framework_observe(self._requirer.on.endpoint_removed, on_change)

    def is_ready(self) -> bool:
        """Check whether the tracing requirer is ready.

        Returns:
            True if the tracing relation is configured and ready.
        """
        return bool(self._requirer and self._requirer.is_ready())

    def ensure_ready(self) -> None:
        """Check that configured tracing relation data is ready.

        Raises:
            RelationDataError: If configured tracing relation data is absent or invalid.
        """
        if not self._requirer:  # not configured
            return
        try:
            relation_data = self._requirer.to_relation_data()
        except InvalidRelationDataError as exc:
            raise RelationDataError(str(exc), self.relation_name) from exc
        if relation_data is None:
            raise RelationDataError("Tracing relation data is not ready", self.relation_name)

    def get_relation_data(self) -> PaaSTracingRelationData | None:
        """Get the tracing relation data.

        Returns:
            The tracing relation data, or None if not configured, not available or invalid.
        """
        if not self._requirer:
            return None
        try:
            return self._requirer.to_relation_data()
        except InvalidTracingRelationDataError:
            return None

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this relation.

        Returns:
            A mapping of environment variable names to values (default ``{}``).
        """
        return self._generate_tracing_env(self.get_relation_data())

    @staticmethod
    def _generate_tracing_env(
        relation_data: PaaSTracingRelationData | None = None,
    ) -> dict[str, str]:
        """Generate environment variables from tracing relation data.

        The tracing integration only provides a traces backend, so the signal specific
        ``OTEL_EXPORTER_OTLP_TRACES_*`` variables are used. Signal specific endpoints are used
        as-is by the SDKs, so the ``/v1/traces`` path is appended to the endpoint path here,
        preserving any query string and fragment.

        Args:
            relation_data: The charm tracing integration relation data.

        Returns:
            Default Tempo tracing environment mappings if relation data is available, empty
            dictionary otherwise.
        """
        if not relation_data:
            return {}
        endpoint = urllib.parse.urlsplit(str(relation_data.endpoint))
        traces_endpoint = urllib.parse.urlunsplit(
            (
                endpoint.scheme,
                endpoint.netloc,
                f"{endpoint.path.rstrip('/')}/v1/traces",
                endpoint.query,
                endpoint.fragment,
            )
        )
        return {
            "OTEL_SERVICE_NAME": relation_data.service_name,
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": traces_endpoint,
            "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL": "http/protobuf",
        }
