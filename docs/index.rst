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
   Reference <reference/index>
   Explanation <explanation/index>
   Changelog <changelog.md>
