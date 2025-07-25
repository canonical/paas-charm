Reference
=========

The Rockcraft and Charmcraft documentation each contain in-depth descriptions of the native
12-factor framework support in the products. The reference pages provide technical
descriptions of the extensions so you can understand their configuration and operation.
The pages detail the project files, requirements, and information about
specific topics such as proxies, background tasks, and secrets.

.. list-table::
  :header-rows: 1
  :widths: 15 20 20

  * - Web app framework
    - Container image profiles
    - Software operator profiles
  * - Django
    - `Rockcraft Django extension <https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/django-framework/>`_
    - `Charmcraft Django extension <https://canonical-charmcraft.readthedocs-hosted.com/en/latest/reference/extensions/django-framework-extension/>`_
  * - Express
    - `Rockcraft Express extension <https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/expressjs-framework/>`_
    - `Charmcraft Express extension <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/express-framework-extension/>`_
  * - FastAPI
    - `Rockcraft FastAPI extension <https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/fastapi-framework/>`_
    - `Charmcraft FastAPI extension <https://canonical-charmcraft.readthedocs-hosted.com/en/latest/reference/extensions/fastapi-framework-extension/>`_
  * - Flask
    - `Rockcraft Flask extension <https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/flask-framework/>`_
    - `Charmcraft Flask extension <https://canonical-charmcraft.readthedocs-hosted.com/en/latest/reference/extensions/flask-framework-extension/>`_
  * - Go
    - `Rockcraft Go extension <https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/go-framework/>`_
    - `Charmcraft Go extension <https://canonical-charmcraft.readthedocs-hosted.com/en/latest/reference/extensions/go-framework-extension/>`_
  * - Spring Boot
    - `Rockcraft Spring Boot extension <https://documentation.ubuntu.com/rockcraft/en/latest/reference/extensions/spring-boot-framework/>`_
    - Coming soon

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
    - `Django extension | Grafana dashboard graphs <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/django-framework-extension/#grafana-dashboard-graphs>`_
    - `Django extension | Relations <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/django-framework-extension/#relations>`_
  * - Express
    - `Express extension | Observability <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/express-framework-extension/#observability>`_
    - `Express extension | Relations <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/express-framework-extension/#relations>`_
  * - FastAPI
    - `FastAPI extension | Observability <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/fastapi-framework-extension/#observability>`_
    - `FastAPI extension | Relations <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/fastapi-framework-extension/#relations>`_
  * - Flask
    - `Flask extension | Grafana dashboard graphs <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/flask-framework-extension/#grafana-dashboard-graphs>`_
    - `Flask extension | Relations <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/flask-framework-extension/#relations>`_
  * - Go
    - `Go extension | Observability <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/go-framework-extension/#observability>`_
    - `Go extension | Relations <https://canonical-charmcraft.readthedocs-hosted.com/latest/reference/extensions/go-framework-extension/#relations>`_
  * - Spring Boot
    - Coming soon
    - Coming soon


All contents
------------

.. toctree::
    :titlesonly:

    juju-events
    Customizable features <supported-customization>
    Changelog <../changelog.md>