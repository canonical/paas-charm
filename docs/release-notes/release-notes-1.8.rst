``paas-charm`` 1.8 release notes
================================

4 August 2025

These release notes cover new features and changes in ``paas-charm``
version 1.8 and its extended support into Charmcraft and Rockcraft.

For more detailed information on Charmcraft and Rockcraft, see their dedicated release notes:

* `Release notes - Rockcraft 1.13 <https://documentation.ubuntu.com/rockcraft/latest/release-notes/rockcraft-1-13/#release-1-13>`_
* Charmcraft support coming soon

See our :ref:`Release policy and schedule <release_policy_schedule>`.

Requirements and compatibility
------------------------------

Using ``paas-charm`` requires the following software:

* ``cosl``
* ``Jinja2`` 3.1.6
* ``jsonschema`` 4.25 or greater
*  ``ops`` 2.6 or greater
* ``pydantic`` 2.11.7

The ``paas-charm`` library is used with Juju charms and runs on a Kubernetes cloud.
For development and testing purposes, a machine or VM with a minimum of 4 CPUs, 4GB RAM,
and a 20GB disk is required.
In production, at least 16GB RAM and 3 high-availability nodes are recommended.

Updates
-------

``paas-charm``
~~~~~~~~~~~~~~

.. vale Canonical.007-Headings-sentence-case = NO

Enhanced support for the Spring Boot extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. vale Canonical.007-Headings-sentence-case = YES

The Spring Boot extension now has additional support for
`SMTP <https://github.com/canonical/paas-charm/pull/101>`_,
`SAML <https://github.com/canonical/paas-charm/pull/103>`_,
`Redis <https://github.com/canonical/paas-charm/pull/109>`_,
`S3 <https://github.com/canonical/paas-charm/pull/110>`_,
`MongoDB <https://github.com/canonical/paas-charm/pull/111>`_,
`MySQL <https://github.com/canonical/paas-charm/pull/112>`_,
`Tracing <https://github.com/canonical/paas-charm/pull/113>`_,
`OpenFGA <https://github.com/canonical/paas-charm/pull/114>`_,
`Observability <https://github.com/canonical/paas-charm/pull/115>`_,
and `RabbitMQ <https://github.com/canonical/paas-charm/pull/119>`_.

These updates align Spring Boot with the other extensions and provide
out-of-the-box integrations with more charms in the Juju ecosystem.

Improved output in Gunicorn logs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you've enabled tracing for your web app and you use the 
X-Request-ID header in your response headers, the Gunicorn access logs
will log the X-Request-ID header to identify a request from the client.

Relevant links:

* `Pull request #121 <https://github.com/canonical/paas-charm/pull/121>`_

Added OIDC support
^^^^^^^^^^^^^^^^^^

All the extensions now have a predefined integration with OIDC.

Relevant links:

* `OIDC support for Flask <https://github.com/canonical/paas-charm/pull/122>`_
* `OIDC support for Django <https://github.com/canonical/paas-charm/pull/124>`_
* `OIDC support for Spring Boot <https://github.com/canonical/paas-charm/pull/131>`_
* `OIDC support for FastAPI <https://github.com/canonical/paas-charm/pull/134>`_
* `OIDC support for Go <https://github.com/canonical/paas-charm/pull/136>`_
* `OIDC support for Express <https://github.com/canonical/paas-charm/pull/137>`_

Updated integration tests
^^^^^^^^^^^^^^^^^^^^^^^^^

The integration tests have been migrated to Jubilant due to the
`deprecation <https://discourse.charmhub.io/t/python-libjuju-3-6-1-3-mind-your-ps-and-qs/18248>`_
of ``python-libjuju``.
Now our integration tests take advantage of enhanced writing and
debugging, and our tests align closer to the Juju CLI experience.


Relevant links:

* `Pull request #104 <https://github.com/canonical/paas-charm/pull/104>`_

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

* Metrics for the Go framework were corrected (`PR #104 <https://github.com/canonical/paas-charm/pull/104>`_).
* Trivy errors were fixed for integration tests to pass (`PR #127 <https://github.com/canonical/paas-charm/pull/127>`_).

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

* `Packing a rock with a restrictive umask <https://github.com/canonical/paas-charm/issues/63>`_
* `FastAPI charm errors out and in loop <https://github.com/canonical/paas-charm/issues/75>`_
* `Per Route Metrics <https://github.com/canonical/paas-charm/issues/98>`_
* `Please encourage using Charmcraft's fetch-libs command instead <https://github.com/canonical/paas-charm/issues/116>`_

Thanks to our contributors
--------------------------

``@alithethird``, ``@javierdelapuente``, ``@erinecon``, ``@M7mdisk``


