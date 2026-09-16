#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm service."""

import logging
import typing

import ops
from charms.temporal_k8s.v0.temporal_host_info import TemporalHostInfoRequirer

import paas_charm.flask
from paas_charm.relations import CustomRelation, InvalidRelationDataError, OnChange

logger = logging.getLogger(__name__)


class TemporalRelation(CustomRelation):
    """Expose Temporal server connection information to the workload."""

    relation_name = "temporal-host-info"

    def setup(self, on_change: OnChange) -> None:
        """Create the Temporal requirer and reconcile when its data changes."""
        self._requirer = TemporalHostInfoRequirer(self.charm)
        self._framework_observe(
            self._requirer.on.temporal_host_info_changed,
            on_change,
        )
        self._framework_observe(
            self._requirer.on.temporal_host_info_unavailable,
            on_change,
        )

    def is_ready(self) -> bool:
        """Return whether the Temporal relation has valid connection information."""
        return self._connection_info() is not None

    def gen_environment(self) -> dict[str, str]:
        """Return Temporal connection information as environment variables."""
        connection_info = self._connection_info()
        if connection_info is None:
            return {}
        host, port = connection_info
        return {"TEMPORAL_HOST": host, "TEMPORAL_PORT": str(port)}

    def _connection_info(self) -> tuple[str, int] | None:
        """Return validated Temporal connection information.

        Returns:
            The Temporal host and port, or None when there is no relation.

        Raises:
            InvalidRelationDataError: If related Temporal data is incomplete or invalid.
        """
        if self._requirer is None or self._requirer.relation is None:
            return None
        try:
            host = self._requirer.host
            port = self._requirer.port
        except (TypeError, ValueError) as exc:
            raise InvalidRelationDataError(
                "invalid Temporal port", relation=self.relation_name
            ) from exc
        if not host or port is None:
            raise InvalidRelationDataError(
                "missing Temporal host or port", relation=self.relation_name
            )
        if not 1 <= port <= 65535:
            raise InvalidRelationDataError(
                "Temporal port must be between 1 and 65535", relation=self.relation_name
            )
        return host, port


class FlaskCharm(paas_charm.flask.Charm):
    """Flask Charm service."""

    custom_relations = [TemporalRelation]

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(FlaskCharm)
