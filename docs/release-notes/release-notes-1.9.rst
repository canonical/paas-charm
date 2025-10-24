``paas-charm`` 1.9 release notes
================================

7 October 2025

These release notes cover new features and changes in ``paas-charm``
version 1.9 and its extended support into Charmcraft and Rockcraft.

For more detailed information on Charmcraft and Rockcraft, see their dedicated release notes:

* `Release notes - Rockcraft 1.14 <https://documentation.ubuntu.com/rockcraft/latest/release-notes/rockcraft-1-14/>`_
* Charmcraft support coming soon

See our :ref:`Release policy and schedule <release_policy_schedule>`.

Requirements and compatibility
------------------------------

Using ``paas-charm`` requires the following software:

* ``cosl``
* ``Jinja2`` 3.1.6
* ``jsonschema`` 4.25 or greater
*  ``ops`` 2.6 or greater
* ``pydantic`` 2.11.9

The ``paas-charm`` library is used with Juju charms and runs on a Kubernetes cloud.
For development and testing purposes, a machine or VM with a minimum of 4 CPUs, 4GB RAM,
and a 20GB disk is required.
In production, at least 16GB RAM and 3 high-availability nodes are recommended.

Updates
-------

``paas-charm``
~~~~~~~~~~~~~~

.. vale Canonical.007-Headings-sentence-case = NO

Added profiles configuration to the Spring Boot extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. vale Canonical.007-Headings-sentence-case = YES

Now the Spring Boot extension has a new configuration option, ``app-profiles``,
that allows you to group and manage parts of your app's configuration based
on the environment in which the app is running. The configuration is
exposed to Spring Boot as the environment variable ``spring.profiles.active``. 

Relevant links:

* `Pull request #172 <https://github.com/canonical/paas-charm/pull/172>`_
* `Spring profiles <https://docs.spring.io/spring-boot/reference/features/profiles.html>`_

.. vale Canonical.007-Headings-sentence-case = NO

Increased Prometheus alert time for Flask and Django extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. vale Canonical.007-Headings-sentence-case = YES

The alert time duration for Flask and Django metric targets has been increased.
Previously, the alerts fired immediately when a metric was marked as down,
meaning failures related to transient network issues or container restarts were reported. 
These types of failures typically resolve themselves quickly and without operator intervention,
so the increased time duration reduces noise and improves the user experience.

Relevant links:

* `Pull request #144 <https://github.com/canonical/paas-charm/pull/144>`_

Rockcraft
~~~~~~~~~

No feature updates in this release.

Charmcraft
~~~~~~~~~~

Coming soon

Backwards-incompatible changes
------------------------------

The following are breaking changes introduced in ``paas-charm``, Rockcraft, and Charmcraft.

``paas-charm``
~~~~~~~~~~~~~~
No breaking changes.

Rockcraft
~~~~~~~~~
No breaking changes.

Charmcraft
~~~~~~~~~~

Coming soon

Bug fixes
---------

The following are bug fixes in ``paas-charm``, Rockcraft, and Charmcraft.

``paas-charm``
~~~~~~~~~~~~~~

* Fixed an issue with the ingress library by refreshing the relation data on every ``update-status``
  hook (`PR #151 <https://github.com/canonical/paas-charm/pull/151>`_)
* Fixed an unintentional removal of a trailing ``/`` character from ``redirect-path``
  (`PR #161 <https://github.com/canonical/paas-charm/pull/161>`_).
* Fixed `Issue #174 <https://github.com/canonical/paas-charm/issues/174>`_ where the RabbitMQ
  relation failed when trying to integrate with non-leader units (`PR #173 <https://github.com/canonical/paas-charm/pull/173>`_).

Rockcraft
~~~~~~~~~~

No bug fixes.

Charmcraft
~~~~~~~~~~

Coming soon

Deprecated features
-------------------

The following features and interfaces will be removed.

``paas-charm``
~~~~~~~~~~~~~~
No deprecated features.

Rockcraft
~~~~~~~~~
No deprecated features.

Charmcraft
~~~~~~~~~~

Coming soon

Known issues in ``paas-charm``
------------------------------

* `Per Route Metrics <https://github.com/canonical/paas-charm/issues/98>`_
* `Migrate paas-charm to use ops.charm_dir instead of os.getcwd <https://github.com/canonical/paas-charm/issues/166>`_

Thanks to our contributors
--------------------------

``@alithethird``, ``@javierdelapuente``, ``@erinecon``, ``@M7mdisk``, ``@seb4stien``, ``@arturo-seijas``


