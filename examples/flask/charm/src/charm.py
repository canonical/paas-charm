#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm service with temporal-host-info custom integration.

This demonstrates the env-var pattern: the temporal-host-info relation
is consumed via TemporalHostInfoRequirer (a charm lib that needs handle.charm),
and the host/port are exposed to the workload as TEMPORAL_HOST / TEMPORAL_PORT
environment variables.

Customers using this pattern: canonical/kernelfactory.canonical.com (engine,
cranker, rebaser charms — Flask and Go).
"""

import logging
import typing

import ops

import paas_charm.flask
from paas_charm.exceptions import InvalidRelationDataError
from paas_charm.integrations import CustomIntegration, IntegrationHandle

try:
    from charms.temporal_k8s.v0.temporal_host_info import TemporalHostInfoRequirer
except ImportError:
    TemporalHostInfoRequirer = None  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)


class TemporalHostInfoIntegration(CustomIntegration):
    """Env-var integration for the temporal-host-info relation.

    Reads ``host`` and ``port`` from the Temporal server's relation databag
    and exposes them as ``TEMPORAL_HOST`` / ``TEMPORAL_PORT`` environment
    variables so the Flask workload can connect to Temporal without
    hard-coding the address.

    Requirer lib: ``charms.temporal_k8s.v0.temporal_host_info``
    Interface:    ``temporal-host-info``
    """

    relation_name = "temporal-host-info"

    def setup(self, handle: IntegrationHandle) -> None:
        """Instantiate the TemporalHostInfoRequirer and observe its events.

        Args:
            handle: Framework handle; handle.charm is forwarded to the lib.
        """
        if TemporalHostInfoRequirer is None:
            logger.warning(
                "temporal_k8s charm lib is not available — "
                "temporal-host-info integration disabled. "
                "Run: charmcraft fetch-lib charms.temporal_k8s.v0.temporal_host_info"
            )
            return

        self._requirer = TemporalHostInfoRequirer(handle.charm)
        handle.observe(
            self._requirer.on.temporal_host_info_changed,
            lambda _: handle.on_change(),
        )
        handle.observe(
            self._requirer.on.temporal_host_info_unavailable,
            lambda _: handle.on_change(),
        )

    def is_ready(self) -> bool:
        """Return True when the requirer has both host and port.

        Returns:
            True when Temporal connection details are available.
        """
        if TemporalHostInfoRequirer is None or not hasattr(self, "_requirer"):
            return False
        return self._requirer.host is not None and self._requirer.port is not None

    def gen_environment(self) -> dict[str, str]:
        """Expose Temporal connection details as workload env vars.

        Raises:
            InvalidRelationDataError: if only one of host/port is present.

        Returns:
            ``TEMPORAL_HOST`` and ``TEMPORAL_PORT`` env vars,
            or ``{}`` when the relation data is not yet available.
        """
        if TemporalHostInfoRequirer is None or not hasattr(self, "_requirer"):
            return {}
        host = self._requirer.host
        port = self._requirer.port
        if host is None and port is None:
            return {}
        if host is None or port is None:
            raise InvalidRelationDataError(
                f"Incomplete temporal-host-info data: host={host!r}, port={port!r}",
                relation=self.relation_name,
            )
        return {
            "TEMPORAL_HOST": host,
            "TEMPORAL_PORT": str(port),
        }


class FlaskCharm(paas_charm.flask.Charm):
    """Flask Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)

    def custom_integrations(self) -> list[CustomIntegration]:
        """Register the temporal-host-info custom integration.

        Returns:
            List containing the TemporalHostInfoIntegration instance.
        """
        return [TemporalHostInfoIntegration]


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(FlaskCharm)
