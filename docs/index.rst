.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

12-Factor app support in Charmcraft and Rockcraft
=================================================

**A simple way to deploy and operate 12-Factor web applications.**

You can use a few simple commands to set up a fully integrated and observable
Kubernetes environment for your web application. This solution, called
12-factor charms, provides an abstraction layer over existing Canonical
products. 12-factor charms are aimed at developers who create applications based
on the `12-factor methodology. <https://12factor.net/>`_

While this page introduces 12-factor charms in the context of
the `Flask framework <https://flask.palletsprojects.com/en/stable/>`_,
the same solution also applies to 12-factor applications built
using the following frameworks:

- Django
- FastAPI
- Go
- Spring Boot (coming soon)

The foundations: Juju, charms and rocks
---------------------------------------

The 12-factor charm solution uses and combines capabilities from the following
Canonical products:

- `Juju <https://juju.is>`_ is an open source orchestration engine for software
  operators that enables the deployment, integration and lifecycle management
  of applications at any scale and on any infrastructure.
- A `charm <https://juju.is/docs/juju/charmed-operator>`_ is an operator -
  business logic encapsulated in reusable software packages that automate every
  aspect of an application's life.
- `Charmcraft <https://canonical-charmcraft.readthedocs-hosted.com/en/stable/>`_
  is a CLI tool that makes it easy and quick to initialize, package, and publish
  charms.
- `Rockcraft <https://documentation.ubuntu.com/rockcraft/en/latest/>`_ is a
  tool to create rocks – a new generation of secure, stable and OCI-compliant
  container images, based on Ubuntu.

A Rockcraft framework (conceptually similar to a `snap
extension <https://snapcraft.io/docs/snapcraft-extensions>`_) is initially
used to facilitate the creation of a well structured, minimal and hardened
container image, called a rock. A Charmcraft profile can then be leveraged to
add a software operator (charm) around the aforementioned container image.

Encapsulating the original 12-factor application in a charm allows your
application to benefit from the entire
`charm ecosystem <https://charmhub.io/>`_, meaning that the app
can be connected to a database, e.g. an HA Postgres, observed through a Grafana
based observability stack, get ingress and much more.

Create a complete development environment in a few commands
-----------------------------------------------------------

Rockcraft natively supports Flask. Production-ready OCI images for your
Flask application can be created using Rockcraft with 3 easy
commands that need to be run in the root directory of the Flask application:

.. code-block:: bash

   sudo snap install rockcraft --classic
   rockcraft init --profile flask-framework
   rockcraft pack

The `full Rockcraft tutorial
<https://documentation.ubuntu.com/rockcraft/en/latest/tutorial/flask.html>`_ for
creating an OCI image for a Flask application takes you from a plain Ubuntu
installation to a production ready OCI image for your Flask application.

Charmcraft also natively supports Flask. You can use it
to create charms that automate every aspect of your Flask
application's life, including integrating with a database, preparing the tables
in the database, integrating with observability and exposing the application
using ingress. From the root directory of the Flask application, the charm for
the application can be created using 4 easy commands:

.. code-block:: bash

   mkdir charm & cd charm
   sudo snap install charmcraft --classic
   charmcraft init --profile flask-framework
   charmcraft pack

The `full getting started tutorial <https://canonical-charmcraft.
readthedocs-hosted.com/en/latest/tutorial/flask/>`_
for creating a charm for a Flask application takes you from a plain Ubuntu
installation to deploying the Flask application on Kubernetes, exposing it using
ingress and integrating it with a database.

Documentation
-------------

Documentation for this project is located in a few places:

1. This site: Documentation related to the product
2. `Rockcraft <https://documentation.ubuntu.com/rockcraft/en/latest/>`_:
   Documentation related to the OCI image containers
3. `Charmcraft <https://canonical-charmcraft.readthedocs-hosted.com/en/stable/>`_:
   Documentation related to the software operators (charms)
4. Coming soon: Documentation related to development

Project and community
---------------------

12-Factor charms are a member of the Ubuntu family. This is an open source
project that warmly welcomes community projects, contributions, suggestions,
fixes and constructive feedback.

* `Code of conduct <https://ubuntu.com/community/ethos/code-of-conduct>`_
* `Get support <https://discourse.charmhub.io/>`_
* `Join our online chat <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_
* Contribute
* Roadmap

Thinking about using 12-Factor charms in your next project? Get in touch!


.. toctree::
   :hidden:
   :maxdepth: 1

   Tutorial <tutorial/index>
   How to <how-to/index>
   Explanation <explanation/index>
