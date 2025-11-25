Reference
=========

The Rockcraft and Charmcraft documentation each contain in-depth descriptions of the native
12-factor framework support in the products. The reference pages provide technical
descriptions of the extensions so you can understand their configuration and operation.
The pages detail the project files, requirements, and information about
specific topics such as environment variables, proxies, background tasks, and secrets.

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

Juju
----

The following pages contain descriptions of topics relevant to
web app deployment with Juju.

* :ref:`Events: A list of Juju hooks relevant to the 12-factor tooling <ref_juju_events>`

Furthermore, the framework support in Charmcraft comes with enabled metrics
and relations depending on the extension. The following table contains links to
the relevant Charmcraft documentation for each web app framework:

.. list-table::
  :header-rows: 1
  :widths: 15 20 20

  * - Web app framework
    - Metrics and tracing
    - Supported integrations
  * - Django
    - :ref:`Django extension | Grafana dashboard graphs <charmcraft:django-grafana-graphs>`
    - :ref:`Django extension | Relations <charmcraft:django-framework-extension-relations>`
  * - Express
    - :ref:`Express extension | Grafana dashboard graphs <charmcraft:express-grafana-graphs>`
    - :ref:`Express extension | Relations <charmcraft:expressjs-framework-extension-relations>`
  * - FastAPI
    - :ref:`FastAPI extension | Grafana dashboard graphs <charmcraft:fastapi-grafana-graphs>`
    - :ref:`FastAPI extension | Relations <charmcraft:fastapi-framework-extension-relations>`
  * - Flask
    - :ref:`Flask extension | Grafana dashboard graphs <charmcraft:flask-grafana-graphs>`
    - :ref:`Flask extension | Relations <charmcraft:flask-framework-extension-relations>`
  * - Go
    - :ref:`Go extension | Grafana dashboard graphs <charmcraft:go-grafana-graphs>`
    - :ref:`Go extension | Relations <charmcraft:go-framework-extension-relations>`
  * - Spring Boot
    - :ref:`Spring Boot extension | Grafana dashboard graphs <charmcraft:spring-boot-grafana-graphs>`
    - :ref:`Spring Boot extension | Relations <charmcraft:spring-boot-framework-extension-relations>`


All contents
------------

.. toctree::
    :titlesonly:

    juju-events
    Customizable features <supported-customization>
    Changelog <../changelog.md>