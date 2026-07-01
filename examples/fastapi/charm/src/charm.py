#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""FastAPI Charm service with ophelia-interface custom integration.

This demonstrates the env-var pattern using raw relation databag access
(no upstream charm lib required). It also demonstrates the bidirectional
case: the integration reads server_address from the remote app and
publishes client_address back to it.

Customers using this pattern:
    EdmilsonRodrigues/ophelia-ci-deployment (ophelia-interface FastAPI charm)
"""

import logging
import typing

import ops

import paas_charm.fastapi
from paas_charm.exceptions import InvalidRelationDataError
from paas_charm.integrations import CustomIntegration, IntegrationHandle

logger = logging.getLogger(__name__)

OPHELIA_RELATION_NAME = "ophelia-server"
CLIENT_PORT = 8008


class OpheliaInterfaceIntegration(CustomIntegration):
    """Env-var integration for the ophelia-interface relation.

    Reads ``server_address`` from the Ophelia server's relation databag
    and exposes it as ``OPHELIA_GRPC_SERVER`` to the FastAPI workload.
    Also publishes ``client_address`` and ``client_version`` back to the
    server on relation changed/joined, mirroring the original charm's
    ``_publish_client_info`` pattern.

    Interface: ophelia-interface (raw databag, no upstream charm lib).
    """

    relation_name = OPHELIA_RELATION_NAME

    def setup(self, handle: IntegrationHandle) -> None:
        """Observe relation events; store handle for databag access.

        Args:
            handle: Framework handle.
        """
        self._handle = handle
        handle.observe(
            handle.on[OPHELIA_RELATION_NAME].relation_joined,
            self._on_relation_joined,
        )
        handle.observe(
            handle.on[OPHELIA_RELATION_NAME].relation_changed,
            self._on_relation_changed,
        )
        handle.observe(
            handle.on[OPHELIA_RELATION_NAME].relation_broken,
            lambda _: handle.on_change(),
        )

    # ------------------------------------------------------------------
    # Private event handlers
    # ------------------------------------------------------------------

    def _on_relation_joined(self, event: ops.RelationJoinedEvent) -> None:
        """Publish our client info when the relation is joined."""
        self._publish_client_info(event.relation)
        self._handle.on_change()

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Publish client info and trigger reconcile when server data changes."""
        self._publish_client_info(event.relation)
        self._handle.on_change()

    def _publish_client_info(self, relation: ops.Relation) -> None:
        """Write client_address and client_version into the unit databag.

        The Ophelia server reads these to discover which clients are connected.

        Args:
            relation: The relation to write into.
        """
        app_name = self._handle.app.name
        relation.data[self._handle.unit]["client_address"] = (
            f"{app_name}:{CLIENT_PORT}"
        )
        relation.data[self._handle.unit]["client_version"] = "1"

    # ------------------------------------------------------------------
    # Touchpoints 2-4: env-var pattern
    # ------------------------------------------------------------------

    def relation_data(self) -> str | None:
        """Return server_address string, or None if not yet available.

        Returns:
            The ``server_address`` value from the remote app databag, or None.

        Raises:
            InvalidRelationDataError: if the app databag exists but ``server_address``
                is missing (indicating partial/malformed data).
        """
        relation = self._handle.model.get_relation(OPHELIA_RELATION_NAME)
        if not relation or not relation.app:
            return None
        app_data = relation.data[relation.app]
        if not app_data:
            return None
        server_address = app_data.get("server_address")
        if server_address is None:
            raise InvalidRelationDataError(
                "ophelia-server relation data present but 'server_address' is missing",
                relation=self.relation_name,
            )
        return server_address

    def gen_environment(self, relation_data: object) -> dict[str, str]:
        """Expose the Ophelia gRPC server address as a workload env var.

        Args:
            relation_data: The server_address string.

        Returns:
            ``OPHELIA_GRPC_SERVER`` env var.
        """
        return {"OPHELIA_GRPC_SERVER": typing.cast(str, relation_data)}


class FastAPICharm(paas_charm.fastapi.Charm):
    """FastAPI Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)

    def custom_integrations(self) -> list[CustomIntegration]:
        """Register the ophelia-interface custom integration.

        Returns:
            List containing the OpheliaInterfaceIntegration instance.
        """
        return [OpheliaInterfaceIntegration()]


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(FastAPICharm)
