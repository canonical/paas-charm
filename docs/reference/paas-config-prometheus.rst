.. _ref_paas_config_prometheus:

Prometheus configuration
========================

The charm publishes a framework scrape job using the top-level ``metrics-port`` and
``metrics-path`` values. The ``prometheus`` section in ``paas-config.yaml`` defines additional
Prometheus scrape targets for metrics collection. Jobs listed in ``scrape_configs`` are appended to
the framework job.

Scrape configuration does not configure the workload listener. Use the top-level ``metrics-port``
and ``metrics-path`` fields for workload environment variables or native framework properties, and
ensure each scrape target matches an endpoint the workload actually serves.

Configuration schema
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

Scrape job example
------------------

The following example publishes one custom scrape job in addition to the framework job:

.. code-block:: yaml

   prometheus:
     scrape_configs:
       - job_name: custom-metrics
         metrics_path: /custom-metrics
         static_configs:
           - targets:
               - "*:9090"

This publishes port ``9090`` and path ``/custom-metrics`` to Prometheus only. It does not alter the
workload environment, create a listener, or probe the endpoint. Configure the workload separately
with top-level ``metrics-port`` and ``metrics-path`` values when needed.

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
       # Custom metrics from all units
       - job_name: "flask-custom-metrics"
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
    * :ref:`Observability and relations <ref_observability_relations>`
