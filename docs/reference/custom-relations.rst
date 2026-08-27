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

.. autoclass:: paas_charm.relations.Context
   :members:
   :noindex:

``paas_charm.relations.OnChange``
----------------------------------

.. autoclass:: paas_charm.relations.OnChange
   :members:
   :noindex:

``paas_charm.relations.CustomRelation``
----------------------------------------

.. autoclass:: paas_charm.relations.CustomRelation
   :members:
   :noindex:

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
stores the instances in the charm state consulted at readiness, env generation, and
reconcile time.

Required vs. optional
~~~~~~~~~~~~~~~~~~~~~

Whether a custom relation is required is read **solely** from the
``optional`` flag of the matching endpoint in ``charmcraft.yaml``:

* ``optional: false`` (or omitted) — a missing relation contributes to
  ``BlockedStatus("missing integrations: <name>")``.
* ``optional: true`` — a missing relation contributes no env vars and never
  blocks.

Error semantics
~~~~~~~~~~~~~~~

``is_ready()`` and ``gen_environment()`` may raise
:class:`paas_charm.exceptions.InvalidRelationDataError` (carrying a
``relation`` attribute). The framework evaluates them inside its existing
invalid-data-catching context and converts the raise into a ``BlockedStatus``
containing the error message. Include the relation name in the error message
if you want it surfaced in the unit status.

.. list-table::
   :header-rows: 1

   * - Situation
     - ``is_ready()``
     - Outcome
   * - Data present but malformed
     - raises ``InvalidRelationDataError(message, relation=...)``
     - ``BlockedStatus(message)``
   * - No relation, or data not usable
     - ``False``
     - optional → no env, no block; required → ``BlockedStatus("missing
       integrations: <name>")``
   * - Data valid and usable
     - ``True``
     - ``gen_environment()`` contributes env vars

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
library. Providing that library is the author's responsibility (for example
via ``charmcraft fetch-lib``). The framework does **not** wrap ``setup()``,
``is_ready()``, or ``gen_environment()`` in ``try/except ImportError``: a
missing author-supplied library surfaces as an ordinary charm error. Authors
who want a softer failure mode guard or defer their own imports.
