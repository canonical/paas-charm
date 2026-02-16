``paas-charm`` 1.10 release notes
=================================

13 February 2026

These release notes cover new features and changes in ``paas-charm``
version 1.10 and its extended support into Charmcraft and Rockcraft.

For more detailed information on Charmcraft and Rockcraft, see their dedicated release notes:

* :ref:`Release notes - Rockcraft 1.17 <rockcraft:release-1.17>`
* :doc:`Release notes - Charmcraft 4.1 <charmcraft:release-notes/charmcraft-4.1>`

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

Prometheus scraping configuration using the new paas-config.yaml configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now new Prometheus scraping targets can be configured using the file ``paas-config.yaml``
This file is an optional configuration file that charm developers can include
in their charm to customize runtime behavior of 12-factor app charms.

Relevant links:

* `Pull request #236 <https://github.com/canonical/paas-charm/pull/236>`_
* `Pull request #242 <https://github.com/canonical/paas-charm/pull/242>`_
* `Pull request #243 <https://github.com/canonical/paas-charm/pull/243>`_
* :ref:`Documentation <ref_paas_config>`

New http-proxy integration support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The new interface ``http_proxy`` is supported in applications created
with the 12-factor tooling, allowing easy configuration for proxies.

* `Pull request #179 <https://github.com/canonical/paas-charm/pull/179>`_

New grafana dashboard for FastAPI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* `Pull request #177 <https://github.com/canonical/paas-charm/pull/177>`_

Rockcraft
~~~~~~~~~

No feature updates in this release.

Charmcraft
~~~~~~~~~~

No feature updates in this release.

Bug fixes
---------

``paas-charm``
~~~~~~~~~~~~~~

* fix: Fix bug in the Grafana Dashboards of Django, Express, FastAPI and Flask
  where when all the variables hold the value `All` (which it does in default), Loki
  throws an error.
* fix: Fixed FastAPI example and changed to use edge PostgreSQL for integration tests.

Known issues in ``paas-charm``
------------------------------

* `Per Route Metrics <https://github.com/canonical/paas-charm/issues/98>`_
* `Migrate paas-charm to use ops.charm_dir instead of os.getcwd <https://github.com/canonical/paas-charm/issues/166>`_
  
Thanks to our contributors
--------------------------

``@alithethird``, ``@javierdelapuente``, ``@erinecon``, ``@swetha1654``, ``@f-atwi``, ``@seb4stien``
