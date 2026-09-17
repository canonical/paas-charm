# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Public extension API for adding custom Juju relations to a 12-factor charm.

This module exposes a small, stable surface that charm authors use to plug
their own Juju relations into the framework lifecycle (environment variables,
readiness/blocking, reconcile/restart) without importing or subclassing
``paas_charm`` internals:

* :class:`Context` — read-only configuration snapshot injected by the framework.
* :class:`OnChange` — protocol of the reconcile callback injected into ``setup``.
* :class:`CustomRelation` — abstract base class authors subclass once per relation.

The exception types :class:`paas_charm.exceptions.InvalidRelationDataError` and
:class:`paas_charm.exceptions.RelationDataError` are part of the public API for
custom relations and are re-exported here for convenience.
"""

import abc
import types
import typing
from dataclasses import dataclass

import ops

from paas_charm.exceptions import InvalidRelationDataError, RelationDataError

__all__ = [
    "Context",
    "OnChange",
    "CustomRelation",
    "InvalidRelationDataError",
    "RelationDataError",
]


# pylint: disable=too-few-public-methods
class OnChange(typing.Protocol):
    """Callback the framework injects via :meth:`CustomRelation.setup`.

    Calling it requests a reconcile/``restart``. Pass ``rerun_migrations=True``
    when the relation change should also re-run database migrations.
    """

    def __call__(self, *, rerun_migrations: bool = False) -> None:
        """Request a reconcile/``restart`` of the workload.

        Args:
            rerun_migrations: when True, also re-run database migrations.
        """


@dataclass(frozen=True)
class Context:
    """Read-only snapshot of the charm's configuration context.

    Passed to each :class:`CustomRelation` at construction time. Provides all
    config-level information a relation needs without accessing paas-charm
    internals. For live state (model, relations, leader status, container
    access) use ``self.charm`` instead.

    Attrs:
        app_name: The Juju application name (e.g. ``"flask-k8s"``).
        framework_name: The 12-factor framework (e.g. ``"flask"``, ``"go"``).
        port: The resolved workload port from ``_workload_config``.
        container_name: The Pebble container name (typically ``"app"``).
        config: Merged framework + user-defined config dict, with Juju-secret
            values resolved.
    """

    app_name: str
    framework_name: str
    port: int
    container_name: str
    config: dict[str, typing.Any]


class CustomRelation(ops.Object, abc.ABC):
    """Author-implemented extension point for a custom Juju relation.

    ``CustomRelation`` subclasses :class:`ops.Object` so that its methods can
    be registered as event observers with ``framework.observe``. Do NOT
    override ``__init__``; the framework calls ``cls(charm)`` automatically and
    injects :attr:`context` before calling :meth:`setup`. Put all setup logic
    in :meth:`setup`.

    ``self.context`` is the primary stable contract and the decoupling
    mechanism — it provides everything a relation needs without coupling it to
    paas-charm internals. ``self.charm`` is an escape hatch for upstream
    requirer charm libraries that require a :class:`ops.CharmBase` instance in
    their constructor (e.g. ``TemporalHostInfoRequirer(self.charm)``). Authors
    who do not need a charm lib should use ``self.context`` exclusively.

    Attrs:
        relation_name: The Juju endpoint name declared in ``charmcraft.yaml``
            (under ``requires`` or ``provides``). Must be set by subclasses.
        required: Whether relation is required or optional.
        charm: The parent charm instance. Prefer ``context`` over ``charm``.
        context: Read-only configuration context injected by the framework.
    """

    relation_name: str = ""

    # The wrapped requirer object, or None if not configured.
    _requirer: typing.Any = None

    # Framework-injected private state. Authors must not set these directly.
    _context: Context | None = None
    _required: bool = False

    def __init__(self, charm: ops.CharmBase) -> None:
        """Initialize the relation as an observed child of the charm.

        Args:
            charm: The parent charm instance.
        """
        super().__init__(charm, self.relation_name)
        self._charm = charm

    @property
    def required(self) -> bool:
        """Whether this relation is required or optional."""
        return self._required

    @property
    def charm(self) -> ops.CharmBase:
        """The parent charm instance.

        Use this only when an upstream requirer charm library requires a
        :class:`ops.CharmBase` in its constructor. For all config-level access
        prefer :attr:`context`.

        Returns:
            The parent charm instance.
        """
        return self._charm

    @property
    def context(self) -> Context:
        """Read-only configuration context injected by the framework.

        Provides ``app_name``, ``framework_name``, ``port``,
        ``container_name``, and merged ``config``.

        Raises:
            RuntimeError: if accessed before the framework has injected it.
        """
        context = self._context
        if context is None:
            raise RuntimeError(
                f"{type(self).__name__}.context accessed before framework injection"
            )
        return context

    def _framework_observe(
        self,
        bound_event: ops.framework.BoundEvent,
        on_change: OnChange,
        rerun_migrations: bool = False,
    ) -> None:
        """Wrap ``on_change`` to satisfy ``framework.observe`` requirements."""
        # create unique bound method per invocation to capture `rerun_migrations`
        observer = lambda self, event: on_change(  # noqa: E731 # pylint: disable=c3001
            rerun_migrations=rerun_migrations
        )
        observer.__name__ = f"_observer_{id(observer):x}"
        bound = types.MethodType(observer, self)
        setattr(self, observer.__name__, bound)
        self.charm.framework.observe(bound_event, bound)

    @abc.abstractmethod
    def setup(self, on_change: OnChange) -> None:
        """Wire event handlers and instantiate requirer objects.

        Called once during charm initialisation. Store the handle (or its
        attributes) for later use in :meth:`is_ready`,
        :meth:`gen_environment`, and :meth:`reconcile`.

        Implementations call ``on_change()`` from each observed event handler;
        the framework routes that to its restart logic. Pass
        ``on_change(rerun_migrations=True)`` to additionally re-run migrations.

        Args:
            on_change: callback requesting a reconcile/``restart``.
        """

    def is_ready(self) -> bool:
        """Return whether this relation is ready.

        Default: ``True`` — the relation never blocks the workload. Env-var
        relations must override this to return ``False`` when the relation is
        absent or data is not yet usable. May raise
        :class:`InvalidRelationDataError`; the framework's
        invalid-data-catching context converts that to ``BlockedStatus``.

        Returns:
            ``True`` when the relation is ready (default).
        """
        return True

    def gen_environment(self) -> dict[str, str]:
        """Return workload environment variables for this relation.

        Called only when :meth:`is_ready` returns ``True``. Read the relation
        bag directly using the handle stored in :meth:`setup` (e.g.
        ``self.charm.model.get_relation(self.relation_name)`` or a requirer
        library property).

        Default returns ``{}`` (no-op for side-effect relations). Raise
        :class:`InvalidRelationDataError` when the bag is present but
        malformed; the framework's error-catching context converts it to
        ``BlockedStatus``.

        Returns:
            A mapping of environment variable names to values (default ``{}``).
        """
        return {}

    def reconcile(self) -> None:
        """Perform side-effect work on every successful restart.

        Called after the main paas-charm reconcile logic is run, only when
        :meth:`is_ready` returns ``True``. Use to push config files, call
        external APIs, or publish relation data. Do NOT call ``on_change()``
        here — that causes an infinite loop. Default is a no-op.
        """
