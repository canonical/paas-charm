.. Copyright 2025 Canonical Ltd.
.. See LICENSE file for licensing details.

12-Factor app support in Charmcraft and Rockcraft
=================================================

**Charmcraft and Rockcraft natively support a simple way
to deploy and operate 12-Factor web applications.**

This support makes it easy to utilize existing Canonical products,
such as databases, ingress and observability, in web applications.
Flask, Django, FastAPI, Go, Express, and Spring Boot are currently
supported with additional frameworks coming soon.

With a few commands, you can set up a fully integrated and observable
Kubernetes environment for your web application. These commands create
production-ready container images for your web application compliant with
the Open Container Initiative (OCI), along with software operators wrapped around
the container images. From there, you can deploy your web application using Juju,
connect it to a database, add ingress and observability and much more. 
Using the built-in support means you don't need prior knowledge 
of Canonical products to get your application up and running --
the support simplifies your source to deployment journey.

The solution is aimed at developers who create applications based on the
`12-factor methodology. <https://12factor.net/>`_ Web developers and operators
can take advantage of the solution to quickly containerize their application,
prepare their projects for deployment, and connect their application to the
features that they need for full-scale production.

In this documentation
---------------------

.. list-table::
   :header-rows: 1

   * -
     -
   * - Get started
     - :doc:`Framework tutorials <tutorial/index>`
   * - Build and deploy
     - :ref:`Manage app rocks <rockcraft:how-to-manage-a-12-factor-app-rock>` |
       :ref:`Manage app charms <charmcraft:manage-12-factor-app-charms>` |
       :ref:`Publish a charm <how_to_publish_charm>`
   * - Application configuration
     - :ref:`Customizable features <ref_supported_customization>` |
       :ref:`paas-config.yaml <ref_paas_config>` |
       :ref:`Tooling conventions <explanation_opinionated_nature>`
   * - Integrations and observability
     - :ref:`Observability and relations <ref_observability_relations>` |
       :ref:`Add custom dashboards and alert rules <how_to_add_custom_cos_assets>` |
       :ref:`Prometheus configuration <ref_paas_config_prometheus>` |
       :ref:`Structured logging <ref_paas_config_structured_logging>`
   * - Concepts and architecture
     - :ref:`12-factor principles <explanation_12_factor_principles_applied>` |
       :ref:`Juju, charms, and rocks <explanation_foundations>` |
       :ref:`Supported web app frameworks <explanation_web_app_frameworks>` |
       :ref:`Charm architecture <ref_charm_architecture>`
   * - Maintenance and extension
     - :ref:`Upgrade an application <how_to_upgrade>` |
       :ref:`Add a framework <how_to_add_new_framework>` |
       :doc:`Release notes <release-notes/index>`

How this documentation is organized
------------------------------------

This documentation uses the
`Diátaxis documentation structure <https://diataxis.fr/>`_.

* :doc:`Tutorials <tutorial/index>` provide hands-on introductions to building
  and deploying apps with supported frameworks.
* :doc:`How-to guides <how-to/index>` provide steps for common development,
  deployment, customization, and maintenance tasks.
* :doc:`Reference <reference/index>` provides technical details about
  configuration, integrations, architecture, and supported features.
* :doc:`Explanation <explanation/index>` provides context about the 12-factor
  methodology, tooling conventions, and product ecosystem.
* :doc:`Release notes <release-notes/index>` describe notable changes and
  upgrade considerations.

Since the tooling is natively part of the Rockcraft and Charmcraft products,
additional documentation is available in their respective documentation sites
under the sections for tutorials, how-to guides, and reference material:

1. :doc:`Rockcraft <rockcraft:index>`:
   Documentation related to the OCI image containers
2. :doc:`Charmcraft <charmcraft:index>`:
   Documentation related to the software operators (charms)

Contributing to this documentation
----------------------------------

Documentation is an important part of this project, and we take the same open-source
approach to the documentation as the code. As such, we welcome community contributions,
suggestions and constructive feedback on our documentation. Our documentation is hosted
on Read The Docs to enable easy collaboration. Please use the "Contribute to this page"
links at the top of each documentation page to either directly change something
you see that's wrong, ask a question, or make a suggestion about a potential change.

If there's a particular area of documentation that you'd like to see that's missing,
please `file a bug <https://github.com/canonical/paas-charm/issues>`_.

Project and community
---------------------

12-Factor web support in Charmcraft and Rockcraft is a member of the Ubuntu family.
This is an open source project that warmly welcomes community projects, contributions,
suggestions, fixes and constructive feedback.

* `Code of conduct <https://ubuntu.com/community/ethos/code-of-conduct>`_
* :ref:`Get support <how_to_get_support>`
* `Join our online chat <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_
* :ref:`Contribute <how_to_contribute>`

Get in touch
~~~~~~~~~~~~

Do you have a project or setup where you want to employ this solution? Reach out
to us on `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_
share your use case and get started!

.. toctree::
   :hidden:
   :maxdepth: 1

   Tutorial <tutorial/index>
   How to <how-to/index>
   Reference <reference/index>
   Explanation <explanation/index>
   Release notes <release-notes/index>
