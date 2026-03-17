``paas-charm`` 1.11 release notes
=================================

16 March 2026

These release notes cover new features and changes in ``paas-charm``
version 1.11 and its extended support into Charmcraft and Rockcraft.

See our :ref:`Release policy and schedule <release_policy_schedule>`.

Requirements and compatibility
------------------------------

Using ``paas-charm`` requires the following software:

* ``cosl``
* ``Jinja2`` 3.1.6
* ``jsonschema`` >=4.26,<4.27
*  ``ops`` 2.6 or greater
* ``pydantic`` 2.12.5

The ``paas-charm`` library is used with Juju charms and runs on a Kubernetes cloud.
For development and testing purposes, a machine or VM with a minimum of 4 CPUs, 4GB RAM,
and a 20GB disk is required.
In production, at least 16GB RAM and 3 high-availability nodes are recommended.

Updates
-------

``paas-charm``
~~~~~~~~~~~~~~

Support for custom COS directories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Users can now provide their own Grafana dashboards, Loki alert rules,
and Prometheus alert rules through custom COS directories.

* `Pull request #250 <https://github.com/canonical/paas-charm/pull/250>`_

RabbitMQ HA support
~~~~~~~~~~~~~~~~~~~~

A new ``RABBITMQ_CONNECT_STRINGS`` environment variable is now available for
applications that use RabbitMQ, enabling high-availability configurations.

* `Pull request #230 <https://github.com/canonical/paas-charm/pull/230>`_

Use ``ops.charm_dir`` instead of ``os.getcwd``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Applications using ``paas-charm`` can now run scenario tests correctly.
The framework now uses ``ops.charm_dir`` to locate charm configuration files
instead of relying on ``os.getcwd()``.

* `Pull request #241 <https://github.com/canonical/paas-charm/pull/241>`_

Structured logging and trace correlation for FastAPI (Uvicorn)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FastAPI applications now support structured logging in JSON format via Uvicorn.
When the application is instrumented with OpenTelemetry, trace context is
automatically correlated in both access and error logs. The logging format
can be configured using the ``paas-config.yaml`` file.

* `Pull request #255 <https://github.com/canonical/paas-charm/pull/255>`_

Structured logging and trace correlation for Django and Flask (Gunicorn)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Django and Flask applications now support structured logging in JSON format
via Gunicorn. When the application is instrumented with OpenTelemetry, trace
context is automatically correlated in both access and error logs. The logging
format can be configured using the ``paas-config.yaml`` file.

* `Pull request #258 <https://github.com/canonical/paas-charm/pull/258>`_

Rockcraft
~~~~~~~~~

No feature updates in this release.

Charmcraft
~~~~~~~~~~

No feature updates in this release.

Bug fixes
---------

No bug fixes in this release.

Known issues in ``paas-charm``
------------------------------

* `Per Route Metrics <https://github.com/canonical/paas-charm/issues/98>`_

Thanks to our contributors
--------------------------

``@f-atwi``, ``@alithethird``, ``@javierdelapuente``

1.11.1 patch release — 17 March 2026
-------------------------------------

``paas-charm`` bug fixes
~~~~~~~~~~~~~~~~~~~~~~~~~

The custom COS directory was previously being merged on every charm event,
causing unnecessary overhead. It is now merged only once, skipping the
operation if the merged directory already exists.

* `Pull request #256 <https://github.com/canonical/paas-charm/pull/256>`_

``paas-charm`` 1.11.1 contributors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``@f-atwi``, ``@alithethird``
