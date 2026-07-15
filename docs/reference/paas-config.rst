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

Use the following key to configure the framework server:

.. list-table::
   :header-rows: 1

   * - Key
     - Type
     - Default
     - Description
   * - ``port``
     - Integer
     - ``8080``
     - Port on which the application server listens.

For example:

.. code-block:: yaml

    port: 8080

The port must be between 1 and 65535. This value is packaged with the charm and
cannot be changed with ``juju config``. If it is omitted, the framework default is used.

Metrics settings are configured under ``prometheus.scrape_configs``. A reserved
job named ``app`` replaces the framework's default metrics endpoint and scrape job.
If the ``app`` job is omitted, the framework metrics defaults are used. In particular,
Spring Boot uses its native Actuator path at ``/actuator/prometheus`` and always
exposes the Prometheus Actuator endpoint.

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
* Configure the application metrics endpoint with the reserved ``app`` scrape job
* Define custom Prometheus scrape targets for metrics collection
* Enable structured framework logs in JSON format

For the detailed configuration schema and detailed examples, see:

.. toctree::
   :maxdepth: 1

   Prometheus configuration <paas-config-prometheus>
   Structured logging configuration <paas-config-structured-logging>
