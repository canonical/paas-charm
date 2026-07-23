.. _ref_paas_config:

paas-config.yaml
================

The ``paas-config.yaml`` file is an optional configuration file that charm developers
can include in their charm to customize runtime behavior of 12-factor app charms.

When used, the ``paas-config.yaml`` file must be placed in the charm root directory
alongside your ``charmcraft.yaml`` file and included in the packed charm file.
The file and all of its keys are optional. Omitted settings use the defaults of the
selected framework.

File structure
--------------

The ``paas-config.yaml`` file uses YAML format and follows a structured schema.
It supports generic application settings in addition to the
``prometheus`` and ``framework_logging_format`` top-level keys.

Application settings
--------------------

Use the following keys to configure the framework server and its metrics endpoint:

.. list-table::
   :header-rows: 1

   * - Key
     - Type
     - Default
     - Description
   * - ``port``
     - Integer
     - Framework-specific
     - Port on which the application server listens.
   * - ``metrics_port``
     - Integer
     - Framework-specific
     - Port on which the workload serves metrics.
   * - ``metrics_path``
     - String
     - Framework-specific
     - Absolute HTTP path on which the workload serves metrics.

For example:

.. code-block:: yaml

    port: 8080
    metrics_port: 8080
    metrics_path: /metrics

Ports must be between 1 and 65535. ``metrics_path`` must start with ``/`` and identify a
non-root endpoint. These values are packaged with the charm and cannot be changed with
``juju config``. Omitted values use the framework defaults.

The default application port is ``8000`` for Flask and Django, and ``8080`` for
FastAPI, ExpressJS, Go, and Spring Boot. The resolved port is always written to the
workload environment when the framework uses an application port environment variable.
Go uses ``PORT``; Flask and Django configure the port directly in Gunicorn instead.

The charm always passes the resolved ``metrics_port`` and ``metrics_path`` values to the workload.
Workload code is responsible for consuming this configuration and exposing the corresponding
endpoint. Flask and Django receive framework-prefixed
``METRICS_PORT`` and ``METRICS_PATH`` variables. FastAPI, ExpressJS, and Go receive unprefixed
variables. Spring Boot receives native ``management.*`` properties.

Flask and Django default to ``9102`` and ``/metrics``. The other frameworks default to ``8080``
and ``/metrics``, except Spring Boot, which uses ``8080`` and ``/actuator/prometheus``.

Prometheus scrape jobs are configured independently under ``prometheus.scrape_configs``. The charm
does not infer or publish a scrape job from ``metrics_port`` and ``metrics_path``. Every desired
scrape job must be explicit, and its target must match an endpoint that the workload actually
serves.

See :ref:`ref_paas_config_prometheus` for detailed Prometheus configuration options.
See :ref:`ref_paas_config_structured_logging` for detailed structured logging options.

Validation
----------

The ``paas-config.yaml`` file is validated when the charm is deployed.
If validation fails, the charm will go into error state and will not work. The
``paas-config.yaml`` file has to be fixed and the charm packed and deployed again.

Common validation errors include:

* Invalid YAML syntax
* Unknown fields
* Missing required fields in nested configuration sections
* Invalid field values

Functionality provided
----------------------

The file ``paas-config.yaml`` allows you to:

* Configure the application server port
* Configure the workload metrics endpoint
* Define custom Prometheus scrape targets for metrics collection
* Enable structured framework logs in JSON format

For the detailed configuration schema and detailed examples, see:

.. toctree::
   :maxdepth: 1

   Prometheus configuration <paas-config-prometheus>
   Structured logging configuration <paas-config-structured-logging>
