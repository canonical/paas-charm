``paas-charm`` 1.12 release notes
=================================

3 July 2026

These release notes cover new features and changes in ``paas-charm``
version 1.12 and its extended support into Charmcraft and Rockcraft.

See our :ref:`Release policy and schedule <release_policy_schedule>`.

Requirements and compatibility
------------------------------

Using ``paas-charm`` requires the following software:

* ``cosl`` 1.9.2
* ``dpcharmlibs-interfaces`` 1.1.0
* ``Jinja2`` 3.1.6
* ``jsonschema`` 4.26.0
* ``ops`` 3.7.1
* ``pydantic`` 2.13.4

The ``paas-charm`` library is used with Juju charms and runs on a Kubernetes cloud.
For development and testing purposes, a machine or VM with a minimum of 4 CPUs, 4GB RAM,
and a 20GB disk is required.
In production, at least 16GB RAM and 3 high-availability nodes are recommended.

Updates
-------

``paas-charm``
~~~~~~~~~~~~~~

No feature updates in this release.

Rockcraft
~~~~~~~~~

No feature updates in this release.

Charmcraft
~~~~~~~~~~

No feature updates in this release.

Backwards-incompatible changes
------------------------------

No breaking changes.

Bug fixes
---------

``paas-charm``
~~~~~~~~~~~~~~

Set ``alert_rules_path`` for ``LogForwarder`` and ``LogProxyConsumer``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``alert_rules_path`` parameter is now correctly set for both
``LogForwarder`` and ``LogProxyConsumer`` when using the v1 version of
the Loki library. Previously, the missing parameter caused custom Loki
alert rules provided through ``cos_custom`` directories to be
ineffective.

* `Pull request #287 <https://github.com/canonical/paas-charm/pull/287>`_

Rockcraft
~~~~~~~~~

No bug fixes to report.

Charmcraft
~~~~~~~~~~

No bug fixes to report.

Deprecated features
-------------------

No deprecated features.

Known issues in ``paas-charm``
------------------------------

* `Per Route Metrics <https://github.com/canonical/paas-charm/issues/98>`_

Thanks to our contributors
--------------------------

``@weiiwang01``, ``@alithethird``, ``@Thanhphan1147``, ``@erinecon``
