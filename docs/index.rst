.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

12-Factor app support in Charmcraft and Rockcraft
=================================================

**Charmcraft and Rockcraft natively support a simple way
to deploy and operate 12-Factor web applications.**

This support makes it easy to utilize existing Canonical products,
such as databases, ingress and observability, in web applications.
Flask, Django, FastAPI and Go are currently supported with additional
frameworks coming soon.

With a few simple commands, you can set up a fully integrated and observable
Kubernetes environment for your web application. These commands create
production-ready OCI-compliant container images for your web application and
software operators wrapped around the container images. From there, you can
deploy your web application, connect it to a database, add ingress and
observability and much more.

The solution is aimed at developers who create applications based on the
`12-factor methodology. <https://12factor.net/>`_ Web developers and operators
can take advantage of the solution to simplify their operations and deploy
their applications to production.

The foundations: Juju, charms and rocks
---------------------------------------

The 12-factor web application solution uses and combines capabilities from the
following Canonical products:

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
based observability stack, add ingress and much more.

Documentation
-------------

Documentation for this project is located in a few places:

1. This site: Documentation related to the product and development
2. `Rockcraft <https://documentation.ubuntu.com/rockcraft/en/latest/>`_:
   Documentation related to the OCI image containers
3. `Charmcraft <https://canonical-charmcraft.readthedocs-hosted.com/en/stable/>`_:
   Documentation related to the software operators (charms)

Contributing to this documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Documentation is an important part of this project, and we take the same open-source
approach to the documentation as the code. As such, we welcome community contributions,
suggestions and constructive feedback on our documentation. Our documentation is hosted
on Read The Docs to enable easy collaboration. Please use the "Edit this page on GitHub"
or "Give Feedback" links on each documentation page to either directly change something
you see that's wrong, ask a question, or make a suggestion about a potential change.

If there's a particular area of documentation that you'd like to see that's missing,
please `file a bug <https://github.com/canonical/paas-charm/issues>`_.

Project and community
---------------------

12-Factor web support in Charmcraft and Rockcraft is a member of the Ubuntu family.
This is an open source project that warmly welcomes community projects, contributions,
suggestions, fixes and constructive feedback.

* `Code of conduct <https://ubuntu.com/community/ethos/code-of-conduct>`_
* `Get support <https://discourse.charmhub.io/>`_
* `Join our online chat <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_
* :ref:`Contribute <how-to-contribute>`
* Roadmap

Thinking about using this solution in your next project? Get in touch!


.. toctree::
   :hidden:
   :maxdepth: 1

   Tutorial <tutorial/index>
   How to <how-to/index>
   Explanation <explanation/index>
   Changelog <changelog.md>
