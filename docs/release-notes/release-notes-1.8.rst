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

For development and testing purposes, a machine or VM with a minimum of 4GB RAM is required.
In production, at least 8GB RAM is recommended per instance.

Upgrade instructions
~~~~~~~~~~~~~~~~~~~~

<detail how to upgrade to this version of ``paas-charm``. If there are no specific
considerations, remove this subsection.>

Updates
-------

``paas-charm``
~~~~~~~~~~~~~~
<List of new major and minor features in the Python library and ``paas-charm``
repo. Include links to pull requests or commits.>

Enhanced support for the Spring Boot extension
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Spring Boot extension now has additional support for
SMTP,
SAML,
Redis,
S3,
MongoDB,
MySQL,
Tracing,
OpenFGA,
Prometheus,
and RabbitMQ.

Improved output in Gunicorn logs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* add X-Request-ID header to Gunicorn logs if present in response.

Added OIDC support
^^^^^^^^^^^^^^^^^^

* Add OIDC support for Flask.
* Add OIDC support for Django.
* Add OIDC support for Spring Boot.
* Add OIDC support for FastAPI.
* Add OIDC support for Go.
* Add OIDC support for Express.

Rockcraft
~~~~~~~~~
<List of new major and minor features in the Rockcraft support. Include links to pull requests or commits.>

* `Documentation changes in the tutorial and reference pages <https://documentation.ubuntu.com/rockcraft/latest/release-notes/rockcraft-1-13/#improved-documentation-for-12-factor-app-extensions>`_

Charmcraft
~~~~~~~~~~
<List of new major and minor features in the Charmcraft support. Include links to pull requests or commits.>

Coming soon

Backwards-incompatible changes
------------------------------

The following are breaking changes introduced in ``paas-charm``, Rockcraft, and Charmcraft.
<If there are no breaking changes in this release, then write "No breaking changes.">

``paas-charm``
~~~~~~~~~~~~~~
<List of breaking changes in the Python library and ``paas-charm`` repo.
Include links to pull requests or commits.>

Rockcraft
~~~~~~~~~
<List of breaking changes in Rockcraft support. Include links to pull requests or commits.>

Charmcraft
~~~~~~~~~~
<List of breaking changes in Charmcraft support. Include links to pull requests or commits.>

Bug fixes
---------

The following are bug fixes in ``paas-charm``, Rockcraft, and Charmcraft.
<If there are no bug fixes to report in this release, then write "No bug fixes to report.">

``paas-charm``
~~~~~~~~~~~~~~
<List of bug fixes in the Python library and ``paas-charm`` repository.
Include links to pull requests or commits.>

Rockcraft
~~~~~~~~~~
<List of relevant bug fixes in the Rockcraft support. Include links to pull requests or commits.>

Charmcraft
~~~~~~~~~~
<List of relevant bug fixes in Charmcraft support. Include links to pull requests or commits.>

Deprecated features
-------------------

The following features and interfaces will be removed.
<If there are no deprecated features in this release, then write "No deprecated features.">

``paas-charm``
~~~~~~~~~~~~~~
<List of deprecated features. Include links to pull requests or commits.>

Charmcraft
~~~~~~~~~~
<List of deprecated features. Include links to pull requests or commits.>

Rockcraft
~~~~~~~~~
<List of deprecated features. Include links to pull requests or commits.>

Known issues in ``paas-charm``
------------------------------

<List of unresolved issues in the ``paas-charm`` repository that are currently being worked
on or are considered important. We don't need to list all of the issues in the
repository here – limit to 3-5 issues. If there are no known issues, then write
"No known issues to report.">

Thanks to our contributors
--------------------------

<List the contributors who worked on ``paas-charm``>


