# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Public API for custom Juju relations in 12-factor charms."""

import abc
import typing

import ops


class OnChange(typing.Protocol):
    """Callback the framework injects into ``setup`` via :class:`IntegrationHandle`.

    Calling it requests a reconcile/``restart``.  Pass
    ``rerun_migrations=True`` when the relation change should also
    re-run database migrations.
    """

    def __call__(self, *, rerun_migrations: bool = False) -> None:
        """Request reconcile/restart.

        Args:
            rerun_migrations: Re-run database migrations on this reconcile.
        """


class IntegrationHandle:
    """Stable handle the framework passes to :meth:`CustomIntegration.setup`.

    Provides everything a custom integration needs without requiring
    authors to import or subclass ``paas_charm`` internals.

    Attrs:
        charm: The :class:`ops.CharmBase` instance. Required by most
            upstream requirer charm libraries (e.g.
            ``TemporalHostInfoRequirer(handle.charm)``).
        config: Merged charm configuration — framework-specific options
            plus user-defined app options — with Juju-secret values
            already resolved.  Read-only within the integration.
        on_change: Callback to trigger reconcile/restart.  Call
            ``handle.on_change(rerun_migrations=True)`` to also re-run
            database migrations.
    """

    def __init__(
        self,
        charm: ops.CharmBase,
        config: dict,
        on_change: OnChange,
    ) -> None:
        """Initialise the handle.

        Args:
            charm: The parent :class:`ops.CharmBase` instance.
            config: Merged, secrets-resolved charm configuration dict.
            on_change: Reconcile/restart callback satisfying
                :class:`OnChange`.
        """
        self._charm = charm
        self._config = config
        self._on_change = on_change

    # ------------------------------------------------------------------
    # Primary attributes
    # ------------------------------------------------------------------

    @property
    def charm(self) -> ops.CharmBase:
        """The parent CharmBase instance.

        Pass this to upstream requirer charm libraries that need it:
        ``MyRequirer(handle.charm)``.
        """
        return self._charm

    @property
    def config(self) -> dict:
        """Merged charm configuration with secrets resolved."""
        return self._config

    @property
    def on_change(self) -> OnChange:
        """Callback to request reconcile/restart."""
        return self._on_change

    # ------------------------------------------------------------------
    # Convenience pass-throughs so simple integrations need not access
    # handle.charm.<attr> directly.
    # ------------------------------------------------------------------

    @property
    def model(self) -> ops.Model:
        """Shortcut for ``handle.charm.model``."""
        return self._charm.model

    @property
    def app(self) -> ops.Application:
        """Shortcut for ``handle.charm.app``."""
        return self._charm.app

    @property
    def unit(self) -> ops.Unit:
        """Shortcut for ``handle.charm.unit``."""
        return self._charm.unit

    @property
    def on(self) -> ops.CharmEvents:
        """Shortcut for ``handle.charm.on`` (event namespace)."""
        return self._charm.on  # type: ignore[return-value]

    @property
    def observe(self) -> typing.Callable:
        """Shortcut for ``handle.charm.framework.observe``."""
        return self._charm.framework.observe


class CustomIntegration(ops.Object, abc.ABC):
    """Author-implemented extension point for a custom Juju relation.

    Subclass this once per custom relation and register the class (not an
    instance) by overriding :meth:`PaasCharm.custom_integrations`.  The
    framework instantiates each class as ``cls(charm)`` so it is properly
    registered as an ``ops.Object`` child — required by
    ``framework.observe``.

    Two usage patterns are supported:

    **Env-var pattern**
        Override :meth:`is_ready` to signal when the relation data is
        usable and :meth:`gen_environment` to return the workload env
        vars.  The framework calls both on every reconcile; env vars are
        merged into the Pebble layer after built-in ones.

    **Side-effect / provides-style pattern**
        Leave :meth:`is_ready` and :meth:`gen_environment` at their
        defaults (``True`` / ``{}``).  Override :meth:`reconcile` to
        push config files, call external APIs, or publish relation data
        on every restart.

    Example (env-var)::

        class TemporalIntegration(CustomIntegration):
            relation_name = "temporal-host-info"

            def setup(self, handle):
                self._requirer = TemporalHostInfoRequirer(handle.charm)
                handle.observe(
                    self._requirer.on.temporal_host_info_changed,
                    lambda _: handle.on_change(),
                )
                handle.observe(
                    self._requirer.on.temporal_host_info_unavailable,
                    lambda _: handle.on_change(),
                )

            def is_ready(self):
                return (
                    self._requirer.host is not None
                    and self._requirer.port is not None
                )

            def gen_environment(self):
                host = self._requirer.host
                port = self._requirer.port
                if host is None or port is None:
                    return {}
                return {
                    "TEMPORAL_HOST": host,
                    "TEMPORAL_PORT": str(port),
                }

    Example (side-effect / provides-style)::

        class NginxRouteIntegration(CustomIntegration):
            relation_name = "nginx-route"

            def setup(self, handle):
                require_nginx_route(
                    charm=handle.charm,
                    service_hostname=handle.app.name,
                    service_name=handle.app.name,
                    service_port=int(handle.config.get("webserver-port", 80)),
                )

            # is_ready() defaults True — never blocks the workload.
            # gen_environment() defaults {} — no env vars produced.

    Note: ``CustomIntegration`` subclasses ``ops.Object`` so that event
    handler methods can be registered with ``framework.observe``.  Do
    **not** override ``__init__``; put all setup logic in
    :meth:`setup` instead.
    """

    relation_name: str
    """Name of the Juju relation endpoint (must match ``charmcraft.yaml``)."""

    def __init__(self, charm: ops.CharmBase):
        """Initialise as an ops.Object child of *charm*.

        Called automatically by the paas-charm framework; do not override.

        Args:
            charm: The parent :class:`ops.CharmBase` instance.
        """
        super().__init__(charm, self.relation_name)

    @abc.abstractmethod
    def setup(self, handle: IntegrationHandle) -> None:
        """Wire event handlers and instantiate requirer objects.

        Called once during charm initialisation.  Store *handle* (or its
        individual attributes) for later use in :meth:`is_ready`,
        :meth:`gen_environment`, and :meth:`reconcile`.

        Args:
            handle: Framework-provided handle giving access to the charm,
                merged config, and the on_change callback.
        """

    # ------------------------------------------------------------------
    # Touchpoint 2 — readiness contribution
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return whether this integration is ready.

        Default: ``True`` — the integration never blocks the workload.

        **Env-var integrations** must override this to return ``False``
        when the relation is absent or its data is not yet usable, so
        the framework can enter ``BlockedStatus`` for required relations
        and skip env-var generation for optional ones.

        May raise
        :class:`~paas_charm.exceptions.InvalidRelationDataError` to
        signal malformed databag content; the framework catches this
        inside its invalid-data context and converts it to a
        ``BlockedStatus`` naming the relation.

        Returns:
            ``True`` when the integration is ready and the workload
            should not be blocked because of it.
        """
        return True

    # ------------------------------------------------------------------
    # Touchpoint 3 — environment variables (env-var pattern)
    # ------------------------------------------------------------------

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this integration.

        Called by the framework on every reconcile **only when**
        :meth:`is_ready` returns ``True``.  Read the relation bag
        directly using the handle stored in :meth:`setup`
        (``self._handle.model.get_relation(self.relation_name)`` or a
        requirer library property).

        The mapping is used verbatim — no per-framework remapping — so
        emit the exact variable names the target framework expects.

        Raise :class:`~paas_charm.exceptions.InvalidRelationDataError`
        when the databag is present but malformed; the framework's
        error-catching context converts it to a ``BlockedStatus``.

        Side-effect integrations that produce no env vars should leave
        this at its default (returns ``{}``).

        Returns:
            A ``dict`` of environment variable names to string values,
            or ``{}`` when there is nothing to contribute.
        """
        return {}

    # ------------------------------------------------------------------
    # Touchpoint 4 — side-effect reconciliation
    # ------------------------------------------------------------------

    def reconcile(self, handle: IntegrationHandle) -> None:
        """Perform side-effect work on every successful restart.

        Called by the framework at the end of
        :meth:`PaasCharm.restart` **after** the Pebble layer has been
        applied, but only when :meth:`is_ready` returns ``True``.

        Use this to push config files into a container, call an
        external API, or publish relation data that depends on the
        workload being up.  Do **not** call ``handle.on_change()``
        from here — that would cause an infinite restart loop.

        The default implementation is a no-op.

        Args:
            handle: The same handle passed to :meth:`setup`.
        """
