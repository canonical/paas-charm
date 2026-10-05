.. meta::
   :description: Release notes for paas-charm 2.0, including new features, backwards-incompatible changes, and the Ubuntu 26.04 LTS migration.

.. _release_notes_2_0:

``paas-charm`` 2.0 release notes
================================

Unreleased

These release notes cover new features and changes in ``paas-charm``
version 2.0 and its extended support into Charmcraft and Rockcraft.

This is a major release that introduces backwards-incompatible changes.
See :ref:`how_to_upgrade` for migration instructions.

For more detailed information on Charmcraft and Rockcraft, see their dedicated release notes:

* :ref:`Release notes - Rockcraft documentation <rockcraft:release-notes>`
* :ref:`Release notes - Charmcraft documentation <charmcraft:release-notes>`

See our :ref:`Release policy and schedule <release_policy_schedule>`.

Requirements and compatibility
------------------------------

``paas-charm`` 2.0 requires Python 3.12 or greater.

All charms and rocks must be rebuilt for Ubuntu 26.04 LTS. Rocks use either
``base: ubuntu@26.04`` or ``base: bare`` with
``build-base: ubuntu@26.04``. Charms use ``base: ubuntu@26.04``.

Charmcraft profiles for Ubuntu 22.04 LTS and Ubuntu 24.04 LTS retain the earlier
generated contract and pin ``paas-charm`` 1.x. They are not a supported path to
``paas-charm`` 2.0.

Upgrade instructions
--------------------

This release requires a manual project migration; ``charmcraft pack`` alone
does not migrate an existing Ubuntu 22.04 LTS or Ubuntu 24.04 LTS project.

Before refreshing a deployment:

1. Migrate and rebuild every rock with an Ubuntu 26.04 LTS base or build base.
2. Migrate and rebuild every charm with ``base: ubuntu@26.04``, the ``uv``
   plugin, ``pyproject.toml`` and ``uv.lock``, and a compatible dependency such
   as ``paas-charm>=2.0.dev1,<3``.
3. Ensure each charm defines the ``app`` container, ``app-image`` resource,
   ``peers`` relation, and a single secret-typed ``app-secret-key`` option. If
   used, stage the charm-owned ``paas-config.yaml`` into the packed charm.
4. Review the :ref:`Backwards-incompatible changes <paas_charm_2_breaking_changes>`
   before refreshing the deployment.

See :ref:`Upgrade to paas-charm 2.0 <how_to_upgrade>` for complete instructions
and links to the current Charmcraft and Rockcraft migration references.

Updates
-------

``paas-charm``
~~~~~~~~~~~~~~

Framework configuration through ``paas-config.yaml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Application and metrics endpoints are now configured through top-level
``port``, ``metrics-port``, and ``metrics-path`` fields in the charm-owned
``paas-config.yaml`` file, alongside the existing structured logging and
Prometheus sections. The charm always exposes the resolved framework defaults
to the workload, and the resolved ``metrics-port`` and ``metrics-path`` are
published as the framework Prometheus scrape job.
This configuration applies to all supported frameworks, including Go. See
:ref:`paas-config.yaml <ref_paas_config>` and
:ref:`Prometheus configuration <ref_paas_config_prometheus>` for details.

* `Pull request #316 <https://github.com/canonical/paas-charm/pull/316>`_
* `Pull request #342 <https://github.com/canonical/paas-charm/pull/342>`_

Custom Prometheus scrape jobs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Additional Prometheus jobs can be declared under ``prometheus.scrape_configs``
without replacing the framework scrape job. Custom targets do not configure the
workload listener; you must ensure each target is actually served. See
:ref:`Prometheus configuration <ref_paas_config_prometheus>` for details.

* `Pull request #316 <https://github.com/canonical/paas-charm/pull/316>`_

Application secret key stored in a Juju secret
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The generated application secret key is now stored in a Juju application-owned
secret instead of the peer relation databag. The ``secret-storage`` peer
relation (and its interface) is renamed to ``peers``, and the peer relation is
now used only for peer coordination such as ``PEER_FQDNS``. The key can be
rotated with the ``rotate-secret-key`` action. See :ref:`Secrets <ref_secrets>`
for details.

* `Pull request #345 <https://github.com/canonical/paas-charm/pull/345>`_

Standardized ``app-secret-key`` configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Secret key configuration is standardized across all frameworks as a single
``app-secret-key`` option of type ``secret`` that accepts a Juju user secret
ID. This replaces the previous string ``app-secret-key`` and
``app-secret-key-id`` options and the framework-specific
``flask-secret-key``/``django-secret-key`` options. Framework-prefixed workload
variables such as ``FLASK_SECRET_KEY`` and ``DJANGO_SECRET_KEY`` are preserved.
See :ref:`Secrets <ref_secrets>` for details.

* `Pull request #367 <https://github.com/canonical/paas-charm/pull/367>`_

OAuth integration migrated to ``charmlibs``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The deprecated ``charms.hydra.v0.oauth`` charm library is replaced with the
maintained ``charmlibs.interfaces.oauth`` package. This is API-compatible with
the previous library. See the
`OAuth interface documentation <https://canonical.com/juju/docs/charmlibs/reference/charmlibs/interfaces/oauth/>`_
for details.

* `Pull request #371 <https://github.com/canonical/paas-charm/pull/371>`_

OpenFGA and tracing integrations migrated to ``charmlibs``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The OpenFGA and tracing integrations now use their maintained ``charmlibs``
interfaces. See the
`OpenFGA interface documentation <https://canonical.com/juju/docs/charmlibs/reference/charmlibs/interfaces/openfga/>`_
and
`tracing interface documentation <https://canonical.com/juju/docs/charmlibs/reference/charmlibs/interfaces/tracing/>`_
for details.

* `Pull request #372 <https://github.com/canonical/paas-charm/pull/372>`_
* `Pull request #373 <https://github.com/canonical/paas-charm/pull/373>`_

OpenFGA store uses the charm application name
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The OpenFGA store name is now derived from the charm application name instead of
a fixed value.

* `Pull request #323 <https://github.com/canonical/paas-charm/pull/323>`_

Rockcraft
~~~~~~~~~

See :ref:`Charm architecture <ref_charm_architecture>` for the workload layout,
and the :ref:`Rockcraft extension reference <rockcraft:reference-extensions>`
for framework-specific configuration.

* Flask and Django application files are placed in ``/app`` with the Gunicorn
  configuration in ``/var/lib/gunicorn`` on the Ubuntu 26.04 LTS base.
  (`Pull request #1348 <https://github.com/canonical/rockcraft/pull/1348>`_)
* Ubuntu 26.04 LTS framework support includes rocks with a bare base and an
  Ubuntu 26.04 LTS build base.
  (`Pull request #1320 <https://github.com/canonical/rockcraft/pull/1320>`_)
* Ubuntu 26.04 LTS framework rocks provide ``/app-data`` as a writable application
  data directory owned by the ``_daemon_`` workload user.
  (`Pull request #1332 <https://github.com/canonical/rockcraft/pull/1332>`_)
* Gunicorn dependencies were updated for Ubuntu 26.04 LTS.
  (`Pull request #1303 <https://github.com/canonical/rockcraft/pull/1303>`_)
* Extension part names may use the ``'.'`` separator on bases that disallow ``/``.
  (`Pull request #1345 <https://github.com/canonical/rockcraft/pull/1345>`_)

Charmcraft
~~~~~~~~~~

See the :ref:`Charmcraft framework extension reference <charmcraft:extensions>`
for the generated charm contract, and
:ref:`Migrate your 12-factor charm to use the uv plugin <uv_migration>` for
dependency management.

* Extension dispatch for 12-factor extensions.
  (`Pull request #2722 <https://github.com/canonical/charmcraft/pull/2722>`_)
* Base-specific ``init`` profiles.
  (`Pull request #2873 <https://github.com/canonical/charmcraft/pull/2873>`_)
* Ubuntu 26.04 LTS framework charms default to non-root.
  (`Pull request #2828 <https://github.com/canonical/charmcraft/pull/2828>`_)
* Validation for ``paas-config.yaml`` and the ``metrics-path`` format.
  (`Pull request #2825 <https://github.com/canonical/charmcraft/pull/2825>`_)
* Alignment of the Ubuntu 26.04 LTS 12-factor charm contract.
  (`Pull request #2884 <https://github.com/canonical/charmcraft/pull/2884>`_)
* Support for Ubuntu 24.04 LTS in supported bases.
  (`Pull request #2766 <https://github.com/canonical/charmcraft/pull/2766>`_)

Until Ubuntu 26.04 LTS framework support is promoted from experimental in the
current tools, set ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1`` when invoking
Rockcraft and ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1`` when invoking
Charmcraft.

.. _paas_charm_2_breaking_changes:

Backwards-incompatible changes
------------------------------

The following are breaking changes introduced in ``paas-charm``.
See :ref:`how_to_upgrade` for migration instructions.

``paas-charm``
~~~~~~~~~~~~~~

Application secret key regeneration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On upgrade, a fresh application secret key is generated because existing values
are not migrated from the former peer databag. Applications that use this key
for session signing (including Flask, Django, FastAPI, ExpressJS, and Spring
Boot) may invalidate existing sessions. Use a ``type: secret`` config option for
user-provided secret material.
(`Pull request #345 <https://github.com/canonical/paas-charm/pull/345>`_)

``secret-storage`` relation renamed to ``peers``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``secret-storage`` peer relation and its interface are renamed to ``peers``.
Charm metadata consumers must use the new endpoint and interface names.
(`Pull request #345 <https://github.com/canonical/paas-charm/pull/345>`_)

``app-secret-key`` configuration option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The string ``app-secret-key`` and separate ``app-secret-key-id`` options, as
well as ``flask-secret-key``/``django-secret-key``, are replaced by a single
``app-secret-key`` option of type ``secret`` that accepts a Juju user secret ID.
Reapply any existing secret key configuration as a Juju secret.
(`Pull request #367 <https://github.com/canonical/paas-charm/pull/367>`_)

Removal of the ``paas_app_charmer`` import path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The deprecated ``paas_app_charmer`` import path is removed. Use
``paas_charm`` instead.
(`Pull request #369 <https://github.com/canonical/paas-charm/pull/369>`_)

Flask and Django application layout and resource names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Flask and Django application root directory is now ``/app`` (matching
FastAPI and ExpressJS), with the mutable ``gunicorn.conf.py`` moved to
``/var/lib/gunicorn``. Access and error logs continue to use stdout and stderr.
Flask and Django rocks must be rebuilt for Ubuntu 26.04 LTS.

The Flask workload container and image resource change from ``flask-app`` and
``flask-app-image`` to ``app`` and ``app-image``. The Django names similarly
change from ``django-app`` and ``django-app-image`` to ``app`` and
``app-image``. Update deployment commands and automation that supply the image
resource; existing applications may need ``--resource app-image=<image>`` when
refreshed.
(`Pull request #352 <https://github.com/canonical/paas-charm/pull/352>`_)

Rockcraft extension part-name separator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Extension-generated Rockcraft part names use ``.`` instead of ``/`` with an
Ubuntu 26.04 LTS effective build base, including bare rocks whose
``build-base`` is Ubuntu 26.04 LTS. Update custom part overrides and references
to use the newly expanded names, such as
``flask-framework.dependencies`` instead of
``flask-framework/dependencies``.

Redis replaced with Valkey
~~~~~~~~~~~~~~~~~~~~~~~~~~

Redis examples and tests are replaced with Valkey. Consumers that still relate
through the ``redis`` endpoint or call ``/redis/*`` must move to the ``valkey``
relation and ``/valkey/*`` endpoints.
(`Pull request #347 <https://github.com/canonical/paas-charm/pull/347>`_)

Loki ``loki_push_api`` v0 removal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Support for the v0 version of the ``loki_push_api`` library is removed. Charms
must use the v1 library.
(`Pull request #374 <https://github.com/canonical/paas-charm/pull/374>`_)

Bug fixes
---------

``paas-charm``
~~~~~~~~~~~~~~

* Use OpenTelemetry auto-instrumentation for metrics in the FastAPI example.
* Serve ExpressJS Prometheus metrics on the configured ``METRICS_PORT``.
* Activate the Spring Boot Valkey example only when a Valkey relation is available.

Charmcraft
~~~~~~~~~~

No bug fixes to report.

Rockcraft
~~~~~~~~~

No bug fixes to report.

Deprecated features
-------------------

The following features and interfaces are removed in this release:

* The ``paas_app_charmer`` import path.
* The ``charms.hydra.v0.oauth`` charm library.
* The v0 ``loki_push_api`` charm library.
* Redis integration in examples and tests.

Thanks to our contributors
--------------------------

``@alithethird``, ``@javierdelapuente``, ``@Thanhphan1147``, ``@weiiwang01``, ``@erinecon``
