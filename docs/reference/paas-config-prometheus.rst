.. _ref_paas_config_prometheus:

Prometheus configuration
========================

The ``prometheus`` section in ``paas-config.yaml`` allows you to define custom
Prometheus scrape targets for metrics collection. This configuration is useful when the default
framework metrics are insufficient for your use case or you want to
expose additional metrics endpoints.

The custom scrape configurations are merged with the default framework
metrics job (if defined), so both can be active when you integrate with Prometheus.

Configuration Schema
--------------------

prometheus
~~~~~~~~~~

The optional top-level ``prometheus`` section contains scrape configuration.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``scrape_configs``
     - List
     - List of scrape job configurations. Optional.

scrape_configs
~~~~~~~~~~~~~~

Each item in ``scrape_configs`` defines a Prometheus scrape job.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``job_name``
     - String
     - Unique name for this scrape job. Required. Must be unique across all jobs.
   * - ``metrics_path``
     - String
     - HTTP path to scrape for metrics. Optional. Default: ``/metrics``
   * - ``static_configs``
     - List
     - List of static target configurations. Required.

static_configs
~~~~~~~~~~~~~~

Each static configuration defines a set of targets and optional labels.

.. list-table::
   :header-rows: 1

   * - Field
     - Type
     - Description
   * - ``targets``
     - List of strings
     - List of target endpoints to scrape. Required. Supports wildcards and placeholders.
   * - ``labels``
     - Dictionary
     - Key-value pairs of labels to attach to all metrics from these targets. Optional.

Target formats
--------------

The ``targets`` field supports several formats:

Wildcard targets
~~~~~~~~~~~~~~~~

Use ``*:PORT`` to target all units in the application on the specified port:

.. code-block:: yaml

   targets:
     - "*:8081"  # Scrapes all units on port 8081

This target expands to the pod IP addresses of all units.

Scheduler-only targets
~~~~~~~~~~~~~~~~~~~~~~

Use ``@scheduler:PORT`` to target only the scheduler services:

.. code-block:: yaml

   targets:
     - "@scheduler:8082"  # Scrapes only scheduler service on port 8082

Scheduler services are guaranteed to run in only one unit. See
:ref:`Worker and Scheduler Services <charmcraft:django-framework-extension-worker-scheduler-services>`.

The ``@scheduler`` placeholder resolves to the fully qualified domain name (FQDN)
of the scheduler unit.

Specific hosts
~~~~~~~~~~~~~~

You can also specify exact hostnames or IP addresses in the targets section. For example:

.. code-block:: yaml

   prometheus:
     scrape_configs:
       # Application metrics from all units
       - job_name: "flask-app-custom"
         metrics_path: "/metrics"
         static_configs:
           - targets:
               - "*:8081"
             labels:
               app: "flask"
               env: "example"

       # Scheduler-specific metrics
       - job_name: "flask-scheduler-metrics"
         metrics_path: "/metrics"
         static_configs:
           - targets:
               - "@scheduler:8082"
             labels:
               role: "scheduler"

Validation rules
----------------

The Prometheus configuration validates the following rules:

1. No extra fields are allowed in the schema.
2. Each ``job_name`` must be unique across all scrape configs.
3. Targets using the ``@scheduler:PORT`` format will require a numeric port.

.. seealso::

    * :ref:`ref_paas_config`
    * :ref:`Metrics and relations <ref_metrics_relations>`
