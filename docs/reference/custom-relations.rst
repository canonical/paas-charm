.. Copyright 2026 Canonical Ltd.
.. See LICENSE file for licensing details.

.. _ref_custom_relations:

Custom relations API reference
==============================

The ``paas_charm.relations`` module is the public, stable extension API for
adding custom Juju relations to a 12-factor charm. It is designed so that
charm authors never need to import or subclass ``paas-charm`` internals.

``paas_charm.relations.Context``
---------------------------------

Read-only snapshot of the charm's configuration context. Provides access to the
Juju application name, 12-factor framework name, workload port, Pebble container
name and merged framework configuration dictionary.

``paas_charm.relations.OnChange``
----------------------------------

Callback provided by the framework for relation to request reconcile/restart
optionally asking to re-run migrations.

``paas_charm.relations.CustomRelation``
----------------------------------------

Author-implemented extension point for a custom Juju relation. Provides a few
helper methods. The main API consists of the following methods:

- ``setup`` — Called once during charm initialisation with appropriate
  ``OnChange`` handler.
- ``ensure_ready`` — The framework uses it to determine whether or not the
  relation is ready. May raise ``RelationDataError`` or
  ``InvalidRelationDataError`` if the relation is not ready because of missing
  or invalid data.
- ``gen_environment`` — called unconditionally. Provides a way for the relation
  to add workload environment variables. Must not raise an exception.

Registration
------------

Register a custom relation by setting the ``custom_relations`` class attribute
on your charm to a list of :class:`~paas_charm.relations.CustomRelation`
subclasses (the class, not an instance):

.. code-block:: python

    class MyCharm(paas_charm.flask.Charm):
        custom_relations = [MyRelation]

The framework instantiates each class as ``cls(charm)``, injects
:class:`~paas_charm.relations.Context` and the required flag (read from the
metadata ``optional`` field), calls ``setup(on_change=self._reconcile)``, and
stores the instances in the charm state consulted at readiness, environment
generation, and reconcile time.

During initialization the framework validates if custom relation is actually
referenced in the ``requires`` mapping of the ``charmcraft.yaml`` and aborts
execution if relation is not listed.

Required vs. optional
~~~~~~~~~~~~~~~~~~~~~

Whether a custom relation is required depends on its definition within the
``requires`` mapping or the ``optional`` flag status of the matching endpoint
in ``charmcraft.yaml``.

If custom relation is explicitly listed in the ``requires`` mapping and its
``optional`` flag is set to ``false`` — it is considered to be required and
a missing relation results in ``BlockedStatus("missing integrations: <name>")``.

Note: by default ``optional`` is set to ``false``, making each custom relation
required. Make sure to explicitly set ``optional: true`` when necessary.

Error semantics
~~~~~~~~~~~~~~~

``ensure_ready()`` may raise :class:`RelationDataError`, or
:class:`InvalidRelationDataError` (carrying a ``relation`` attribute) when the
relation is not ready or relation data is missing or malformed. The framework
calls ``ensure_ready()`` for every established relation and converts any raised
exception into ``BlockedStatus("RelationDataError: <exception message>")``.
The same information is logged with the ``ERROR`` priority.

Relations must not be raising exceptions from ``get_environment()``, doing so
will block the charm.

.. list-table::
   :header-rows: 1

   * - Situation
     - ``ensure_ready()``
     - Outcome
   * - Data present but malformed
     - raises ``InvalidRelationDataError(message, relation=...)``
     - ``BlockedStatus("missing integrations: <name>")``, whether the relation is
       optional or required
   * - No relation
     - not called
     - required → ``BlockedStatus("missing integrations: <name>")``; optional →
       no environment, no block
   * - Related but data not usable
     - raises ``RelationDataError``
     - ``BlockedStatus("missing integrations: <name>")``, whether the relation is
       optional or required
   * - Data valid and usable → ``gen_environment()`` contributes environment variables
       and usable
     - called always, even when relation is not ready
     - must return without raising

Event observation helper
~~~~~~~~~~~~~~~~~~~~~~~~

``CustomRelation`` provides a helper method :meth:`_framework_observe` to wire
Juju events to the framework's ``on_change`` callback:

.. code-block:: python

    self._framework_observe(
        self.charm.on[self.relation_name].relation_changed,
        on_change,
        rerun_migrations=True,
    )

This binds ``on_change`` as an observer method on the relation instance,
satisfying the Ops framework's requirement that observers be bound methods of
an ``ops.Object``.

Public exception types
~~~~~~~~~~~~~~~~~~~~~~

The following exception types are part of the public API surface for custom
relations and are re-exported from ``paas_charm.relations``:

* :class:`paas_charm.exceptions.InvalidRelationDataError`
* :class:`paas_charm.exceptions.RelationDataError`

Single canonical env-var mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Custom relations produce a single canonical env-var mapping, authored directly
in ``gen_environment``, used as-is across the framework. A 12-factor charm
targets exactly one framework, so the author always knows which environment
variable names that framework's workload expects and can emit them directly.
Per-framework remapping for custom relations is out of scope.

Optional charm libraries
~~~~~~~~~~~~~~~~~~~~~~~~

A custom relation's requirer typically imports an author-supplied charm
library. Providing that library is the author's responsibility. The framework
does **not** wrap ``setup()`` and ``gen_environment()`` in
``try/except ImportError``: a missing author-supplied library surfaces as an
ordinary charm error. Authors who want a softer failure mode guard or defer
their own imports. Since ``gen_environment()`` call is not wrapped in
``try/except``, relations should not intentionally raise an exception when
creating environment variables.
