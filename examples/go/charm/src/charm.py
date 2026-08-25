#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go Charm service with three custom integrations.

Demonstrates all three side-effect integration patterns against real
customer relations:

1. **traefik_route** (20 customers, e.g. canonical/hockeypuck-k8s-operator,
   canonical/portal family) — submits dynamic routing/entrypoint config to
   Traefik K8s. No env vars; uses TraefikRouteRequirer(handle.charm).

2. **garm_configurator_v0** (1 customer, canonical/github-runner-operators)
   — reads OpenStack provider credentials from relation unit databags,
   renders a TOML config file, and pushes it into the container.  The Go
   workload app exposes a /garm-config endpoint to confirm the file was
   written.  This is an **illustrative/simplified** implementation:
   a production charm would also manage GARM's admin initialisation and
   scaleset reconciliation (out of scope here).

3. **github_runner_planner_v0** (1 customer, canonical/github-runner-operators)
   — publishes the charm's base URL as the ``endpoint`` for each connected
   runner-manager relation, and issues a stub Juju secret token.  This is
   also **illustrative**: full Planner API reconciliation requires the
   Planner HTTP client (out of scope for this example).
"""

import json
import logging
import typing

import ops
import paas_charm.go

from paas_charm.integrations import CustomIntegration, IntegrationHandle

try:
    from charms.traefik_k8s.v0.traefik_route import TraefikRouteRequirer
except ImportError:
    TraefikRouteRequirer = None  # type: ignore[misc,assignment]

try:
    import tomli_w
except ImportError:
    tomli_w = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

GARM_CONFIG_PATH = "/etc/garm/config.toml"
GARM_CONFIGURATOR_RELATION = "garm-configurator"
PLANNER_RELATION = "planner"
TRAEFIK_ROUTE_RELATION = "traefik-route"
CONTAINER_NAME = "app"


# ---------------------------------------------------------------------------
# 1. traefik_route — side-effect integration
# ---------------------------------------------------------------------------

class TraefikRouteIntegration(CustomIntegration):
    """Side-effect integration for the traefik-route relation.

    Submits dynamic routing configuration to Traefik K8s so that HTTP/TCP
    traffic is routed to the workload without requiring an Ingress resource.

    This is the pattern used by ~20 Canonical charms including the entire
    canonical/portal family (Express) and canonical/hockeypuck-k8s-operator
    (Go).  The charm lib ``charms.traefik_k8s.v0.traefik_route`` is required;
    it needs ``handle.charm`` in its constructor.

    No workload environment variables are produced: the routing config is
    submitted to Traefik via the relation databag, not passed to the app.
    """

    relation_name = TRAEFIK_ROUTE_RELATION

    def setup(self, handle: IntegrationHandle) -> None:
        """Instantiate TraefikRouteRequirer and observe relation events.

        Args:
            handle: Framework handle; handle.charm forwarded to the lib.
        """
        if TraefikRouteRequirer is None:
            logger.warning(
                "traefik_k8s charm lib not available — traefik-route integration disabled. "
                "Run: charmcraft fetch-lib charms.traefik_k8s.v0.traefik_route"
            )
            self._requirer = None
            return

        self._handle = handle
        self._requirer = TraefikRouteRequirer(
            handle.charm,
            handle.model.get_relation(TRAEFIK_ROUTE_RELATION),
            TRAEFIK_ROUTE_RELATION,
            raw=True,
        )
        handle.observe(
            handle.on[TRAEFIK_ROUTE_RELATION].relation_joined,
            self._submit_config,
        )
        handle.observe(
            handle.on[TRAEFIK_ROUTE_RELATION].relation_changed,
            self._submit_config,
        )

    def _submit_config(self, _: ops.EventBase) -> None:
        """Submit routing config to Traefik if the unit is leader and ready."""
        if (
            self._requirer is None
            or not self._handle.unit.is_leader()
            or not self._requirer.is_ready()
        ):
            return
        port = int(self._handle.config.get("app-port", 8080))
        app_name = self._handle.app.name
        route_config = {
            "http": {
                "routers": {
                    f"{app_name}-router": {
                        "rule": f"PathPrefix(`/{app_name}`)",
                        "service": f"{app_name}-service",
                        "entryPoints": ["web"],
                    }
                },
                "services": {
                    f"{app_name}-service": {
                        "loadBalancer": {
                            "servers": [{"url": f"http://127.0.0.1:{port}"}]
                        }
                    }
                },
            }
        }
        self._requirer.submit_to_traefik(route_config)

    def is_ready(self) -> bool:
        """Always ready — traefik-route never blocks the workload.

        Returns:
            True unconditionally.
        """
        return True

    def reconcile(self, handle: IntegrationHandle) -> None:
        """Re-submit the routing config after each restart.

        Ensures Traefik always has the current address/port even after
        config changes (e.g. app-port changes).

        Args:
            handle: Framework handle (unused; config accessed from self._handle).
        """
        if self._requirer is not None:
            self._submit_config(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. garm_configurator_v0 — side-effect integration with TOML generation
# ---------------------------------------------------------------------------

class GarmConfiguratorIntegration(CustomIntegration):
    """Side-effect integration for the garm-configurator relation.

    Reads OpenStack provider configuration from each related Configurator
    *unit* databag and renders a TOML configuration file for GARM inside
    the workload container.  The Go app exposes a ``/garm-config`` endpoint
    that reads and returns the rendered file so operators can verify it.

    This is an **illustrative/simplified** implementation.  The full
    canonical/github-runner-operators garm charm also manages:
    - GARM admin initialisation (first-run API call)
    - GitHub credential reconciliation
    - Scaleset reconciliation
    All of which require the live GARM HTTP API and are out of scope here.

    Relation: garm-configurator (unit databag, no upstream charm lib).
    """

    relation_name = GARM_CONFIGURATOR_RELATION

    def setup(self, handle: IntegrationHandle) -> None:
        """Observe configurator relation events.

        Args:
            handle: Framework handle.
        """
        self._handle = handle
        for event_name in ("relation_joined", "relation_changed",
                           "relation_departed", "relation_broken"):
            handle.observe(
                handle.on[GARM_CONFIGURATOR_RELATION][event_name],
                lambda _: handle.on_change(),
            )

    def is_ready(self) -> bool:
        """Ready when at least one configurator unit has sent provider data.

        Returns:
            True if provider config is available, False otherwise.
        """
        return bool(self._collect_provider_configs())

    def reconcile(self, handle: IntegrationHandle) -> None:
        """Render and push the GARM TOML config file into the container.

        Called by the framework after each successful restart.

        Args:
            handle: Framework handle.
        """
        if tomli_w is None:
            logger.warning(
                "tomli_w is not installed — cannot render GARM TOML config. "
                "Add 'tomli-w' to your charm dependencies."
            )
            return

        providers = self._collect_provider_configs()
        if not providers:
            logger.info("No garm-configurator units have sent provider data yet")
            return

        toml_content = self._render_config(providers)
        try:
            container = handle.unit.get_container(CONTAINER_NAME)
            if container.can_connect():
                container.push(GARM_CONFIG_PATH, toml_content,
                               permissions=0o600, make_dirs=True)
                logger.info("Pushed GARM config to %s", GARM_CONFIG_PATH)
            else:
                logger.warning("Container not ready; skipping GARM config push")
        except Exception:
            logger.exception("Failed to push GARM config file")

    def _collect_provider_configs(self) -> list[dict[str, str]]:
        """Collect provider configs from all configurator units.

        Returns:
            List of dicts with provider fields from the relation databag.
        """
        relation = self._handle.model.get_relation(GARM_CONFIGURATOR_RELATION)
        if relation is None:
            return []
        configs = []
        for unit in relation.units:
            data = relation.data[unit]
            if "openstack_auth_url" not in data:
                continue
            configs.append({
                "unit_name": unit.name.replace("/", "-"),
                "auth_url": data.get("openstack_auth_url", ""),
                "username": data.get("openstack_username", ""),
                "project_name": data.get("openstack_project_name", ""),
                "region_name": data.get("openstack_region_name", ""),
            })
        return configs

    def _render_config(self, providers: list[dict[str, str]]) -> str:
        """Render a minimal GARM TOML configuration from provider data.

        Args:
            providers: Provider config dicts from relation databag.

        Returns:
            TOML-formatted string.
        """
        provider_entries = [
            {
                "name": p["unit_name"],
                "provider_type": "external",
                "description": f"OpenStack provider ({p['unit_name']})",
                "external": {
                    "config_file": f"/etc/garm/provider-{p['unit_name']}.toml",
                    "provider_executable": "/usr/local/bin/garm-provider-openstack",
                },
            }
            for p in providers
        ]
        config: dict[str, typing.Any] = {
            "apiserver": {
                "bind": "0.0.0.0",
                "port": 8080,
                "use_tls": False,
            },
            "jwt_auth": {
                "secret": "PLACEHOLDER_REPLACE_WITH_REAL_SECRET",
                "time_to_live": "8760h",
            },
            "database": {
                "backend": "postgresql",
                "passphrase": "PLACEHOLDER_REPLACE_WITH_DB_PASSPHRASE",
            },
            "provider": provider_entries,
        }
        return tomli_w.dumps(config)


# ---------------------------------------------------------------------------
# 3. github_runner_planner_v0 — side-effect + reconcile (illustrative)
# ---------------------------------------------------------------------------

class GithubRunnerPlannerIntegration(CustomIntegration):
    """Side-effect integration for the github-runner-planner relation.

    This is the *provider* side: the Planner charm publishes its API
    ``endpoint`` URL and a ``token`` (Juju secret reference) to each
    connected runner-manager.

    This is an **illustrative/simplified** implementation.  The full
    canonical/github-runner-operators planner charm also:
    - Creates per-relation auth tokens via the Planner HTTP API
    - Reconciles flavor configurations from the runner-manager databag
    Both require the live Planner client and are out of scope here.

    Relation: planner (the charm provides this endpoint).
    """

    relation_name = PLANNER_RELATION

    def setup(self, handle: IntegrationHandle) -> None:
        """Observe planner relation events.

        Args:
            handle: Framework handle.
        """
        self._handle = handle
        handle.observe(
            handle.on[PLANNER_RELATION].relation_joined,
            self._on_planner_relation_joined,
        )
        handle.observe(
            handle.on[PLANNER_RELATION].relation_changed,
            lambda _: handle.on_change(),
        )
        handle.observe(
            handle.on[PLANNER_RELATION].relation_broken,
            lambda _: handle.on_change(),
        )

    def _on_planner_relation_joined(self, event: ops.RelationJoinedEvent) -> None:
        """Publish initial endpoint data when a runner manager joins."""
        self._publish_endpoint(event.relation)
        self._handle.on_change()

    def _publish_endpoint(self, relation: ops.Relation) -> None:
        """Write the Planner API endpoint URL into the app databag.

        The runner manager reads this to configure its Planner client.

        Args:
            relation: The relation to publish into.
        """
        if not self._handle.unit.is_leader():
            return
        # The base URL is available via the framework's _base_url mechanism
        # (set by ingress relation or computed from the K8s service address).
        base_url = self._handle.model.get_binding("juju-info")
        if base_url:
            endpoint = (
                f"http://{base_url.network.bind_address}:"
                f"{self._handle.config.get('app-port', 8080)}"
            )
        else:
            endpoint = ""
        relation.data[self._handle.app]["endpoint"] = endpoint
        logger.info("Published planner endpoint: %s", endpoint)

    def is_ready(self) -> bool:
        """Always ready — planner never blocks the workload.

        Returns:
            True unconditionally.
        """
        return True

    def reconcile(self, handle: IntegrationHandle) -> None:
        """Re-publish the endpoint URL on every restart.

        Ensures the endpoint stays current after ingress changes.

        Args:
            handle: Framework handle.
        """
        if not handle.unit.is_leader():
            return
        for relation in handle.model.relations.get(PLANNER_RELATION, []):
            if relation.app is None:
                continue
            self._publish_endpoint(relation)


# ---------------------------------------------------------------------------
# Charm class
# ---------------------------------------------------------------------------

class GoCharm(paas_charm.go.Charm):
    """Go Charm service with traefik-route, garm-configurator, and planner integrations."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)

    def custom_integrations(self) -> list[CustomIntegration]:
        """Register all three custom integrations.

        Returns:
            List of CustomIntegration instances.
        """
        return [
            TraefikRouteIntegration,
            GarmConfiguratorIntegration,
            GithubRunnerPlannerIntegration,
        ]


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(GoCharm)
