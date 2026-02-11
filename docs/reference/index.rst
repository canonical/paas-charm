Reference
=========

The following pages provide technical descriptions on the individual components in the
12-factor framework support.

Extensions in Rockcraft and Charmcraft
--------------------------------------

The Rockcraft and Charmcraft documentation each contain in-depth descriptions of the native
12-factor framework support in the products:

* :ref:`Rockcraft extensions <rockcraft:reference-extensions>`: Technical descriptions of the
  extensions for 12-factor app container images.
* :ref:`Charmcraft extensions <charmcraft:extensions>`: Technical descriptions of the extensions
  for 12-factor app charms.

The reference pages provide technical
descriptions of the extensions so you can understand their configuration and operation.
The pages detail the project files, requirements, and information about
specific topics such as environment variables, proxies, background tasks, and secrets.
The following table contains links to pages for the individual extensions.

.. list-table::
  :header-rows: 1
  :widths: 15 20 20

  * - Web app framework
    - Container image profiles
    - Software operator profiles
  * - Django
    - :ref:`Rockcraft Django extension <rockcraft:reference-django-framework>`
    - :ref:`Charmcraft Django extension <charmcraft:django-framework-extension>`
  * - Express
    - :ref:`Rockcraft Express extension <rockcraft:reference-express-framework>`
    - :ref:`Charmcraft Express extension <charmcraft:expressjs-framework-extension>`
  * - FastAPI
    - :ref:`Rockcraft FastAPI extension <rockcraft:reference-fastapi-framework>`
    - :ref:`Charmcraft FastAPI extension <charmcraft:fastapi-framework-extension>`
  * - Flask
    - :ref:`Rockcraft Flask extension <rockcraft:reference-flask-framework>`
    - :ref:`Charmcraft Flask extension <charmcraft:flask-framework-extension>`
  * - Go
    - :ref:`Rockcraft Go extension <rockcraft:reference-go-framework>`
    - :ref:`Charmcraft Go extension <charmcraft:go-framework-extension>`
  * - Spring Boot
    - :ref:`Rockcraft Spring Boot extension <rockcraft:reference-spring-boot-framework>`
    - :ref:`Charmcraft Spring Boot extension <charmcraft:spring-boot-framework-extension>`

12-factor app charm
-------------------

The following pages provide more information about the software operator built with Charmcraft.

* :ref:`Metrics and relations <ref_metrics_relations>`: A list of pages with technical descriptions
  about the enabled metrics and relations supported in the 12-factor app support in Charmcraft.
* :ref:`Charm architecture <ref_charm_architecture>`: An overview of the architecture,
  components, and source code.
* :ref:`paas-config.yaml <ref_paas_config>`: Configuration file for customizing charm runtime behavior.

Juju
----

The following pages contain descriptions of topics relevant to
web app deployment with Juju.

* :ref:`Events <ref_juju_events>`: A list of Juju hooks relevant to the 12-factor tooling.

Project features and changes
----------------------------

The following pages provide more information about the 12-factor project.

* :ref:`ref_supported_customization`: A list of customizable features in 12-factor app rocks and charms.
* :ref:`changelog`: A list of notable changes in the ``paas-charm`` project.

.. toctree::
    :hidden:
    :titlesonly:

    Rockcraft extensions <https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/>
    Charmcraft extensions <https://documentation.ubuntu.com/charmcraft/latest/reference/extensions/>
    paas-config
    metrics-relations
    charm-architecture
    juju-events
    Customizable features <supported-customization>
    Changelog <../changelog.md>
