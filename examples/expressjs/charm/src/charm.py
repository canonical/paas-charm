#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""ExpressJS Charm service with nginx-route custom integration.

Demonstrates the side-effect pattern: the nginx-route relation publishes
routing configuration to nginx-ingress-integrator so the ExpressJS workload
is reachable via Nginx ingress — without any workload environment variables
being produced.

Customers using this pattern: ~8 Canonical charms including
canonical/directory-api (Go), canonical/marketing.canonical.com (Flask),
canonical/lago-api-operator, canonical/specs.canonical.com (Go), and others.

The ``require_nginx_route`` helper from the nginx-ingress-integrator charm
lib needs ``handle.charm``, which is available via IntegrationHandle.
"""

import logging
import typing

import ops

import paas_charm.expressjs
from paas_charm.integrations import CustomIntegration, IntegrationHandle

try:
    from charms.nginx_ingress_integrator.v0.nginx_route import require_nginx_route
except ImportError:
    require_nginx_route = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

NGINX_ROUTE_RELATION = "nginx-route"


class NginxRouteIntegration(CustomIntegration):
    """Side-effect integration for the nginx-route relation.

    Calls ``require_nginx_route`` to wire the relation and push the service
    hostname, name, and port to nginx-ingress-integrator so it creates the
    correct Kubernetes Nginx Ingress resource.  No workload environment
    variables are produced.

    Requirer helper: ``charms.nginx_ingress_integrator.v0.nginx_route``
    Interface:       ``nginx-route``
    """

    relation_name = NGINX_ROUTE_RELATION

    def setup(self, handle: IntegrationHandle) -> None:
        """Call require_nginx_route to wire event handlers.

        ``require_nginx_route`` must be called in __init__ (i.e. during
        charm setup) for the relation-changed handler to be properly
        registered — which is exactly what the framework guarantees by
        calling setup() during PaasCharm.__init__.

        The service port is read from the merged config so it stays in
        sync with operator-configured ``webserver-port`` changes.

        Args:
            handle: Framework handle; handle.charm forwarded to the helper.
        """
        if require_nginx_route is None:
            logger.warning(
                "nginx_ingress_integrator charm lib not available — "
                "nginx-route integration disabled. "
                "Run: charmcraft fetch-lib "
                "charms.nginx_ingress_integrator.v0.nginx_route"
            )
            return

        self._handle = handle
        port = int(handle.config.get("webserver-port", 8080))

        require_nginx_route(
            charm=handle.charm,
            service_hostname=handle.app.name,
            service_name=handle.app.name,
            service_port=port,
        )

    def is_ready(self) -> bool:
        """Always ready — nginx-route never blocks the workload.

        The charm starts serving as soon as it's ready; nginx-ingress-integrator
        routes traffic in asynchronously.

        Returns:
            True unconditionally.
        """
        return True


class ExpressJSCharm(paas_charm.expressjs.Charm):
    """ExpressJS Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)

    def custom_integrations(self) -> list[CustomIntegration]:
        """Register the nginx-route custom integration.

        Returns:
            List containing the NginxRouteIntegration instance.
        """
        return [NginxRouteIntegration()]


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(ExpressJSCharm)
