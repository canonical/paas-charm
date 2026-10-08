.. _ref_paas_config:

paas-config.yaml
================

The ``paas-config.yaml`` file is an optional configuration file that charm developers
can include in their charm to customize runtime behavior of 12-factor app charms.

When used, the ``paas-config.yaml`` file must be placed in the charm root directory
alongside your ``charmcraft.yaml`` file and included in the packed charm file.
For packaging with the ``uv`` plugin, see
:doc:`the packaging instructions </how-to/uv-migration>`.
The file and all of its keys are optional. Omitted settings use the defaults of the
selected framework.
This file is distinct from charm configuration options managed through ``juju config``.

File structure
--------------

The ``paas-config.yaml`` file uses YAML format and follows a structured schema.
It supports generic application settings in addition to the
``prometheus``, ``framework_logging_format``, and ``config`` top-level keys.

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
   * - ``metrics-port``
     - Integer
     - Framework-specific
     - Port on which the workload serves metrics.
   * - ``metrics-path``
     - String
     - Framework-specific
     - Absolute HTTP path on which the workload serves metrics.

For example:

.. code-block:: yaml

    port: 8080
    metrics-port: 8080
    metrics-path: /metrics

Ports must be between 1 and 65535. ``metrics-path`` must start with ``/`` and identify a
non-root endpoint. These values are packaged with the charm and cannot be changed with
``juju config``. Omitted values use the framework defaults.

The default application port is ``8000`` for Flask, Django, and FastAPI, and ``8080`` for
ExpressJS, Go, and Spring Boot. The resolved port is always written to the
workload environment when the framework uses an application port environment variable.
Go uses ``PORT``; Flask and Django configure the port directly in Gunicorn instead.

The charm always passes the resolved ``metrics-port`` and ``metrics-path`` values to the workload.
Workload code is responsible for consuming this configuration and exposing the corresponding
endpoint. Flask and Django receive framework-prefixed
``METRICS_PORT`` and ``METRICS_PATH`` variables. FastAPI, ExpressJS, and Go receive variables
without framework prefixes. Spring Boot receives native ``management.*`` properties.

Flask and Django default to ``9102`` and ``/metrics``. Go default to ``8080``
and ``/metrics``, Spring Boot, which uses ``8080`` and ``/actuator/prometheus``, and ExpressJS and
FastAPI default to ``9464`` and ``/metrics``.

The charm publishes a Prometheus scrape job for the resolved ``metrics-port`` and ``metrics-path``.
Additional scrape jobs can be configured independently under ``prometheus.scrape_configs``. Their
targets must match endpoints that the workload actually serves.

See :ref:`ref_paas_config_prometheus` for detailed Prometheus configuration options.
See :ref:`ref_paas_config_structured_logging` for detailed structured logging options.

Environment variable name mappings
----------------------------------

Use ``config.options`` to rename environment variables generated from charm configuration
options, including framework-provided options. Mappings refer to existing options; they
do not declare options or set their values.

This example assumes ``log-level`` is a string option and ``credentials`` has ``type: secret``:

.. code-block:: yaml
   :caption: paas-config.yaml

    config:
      options:
        log-level:
          env-var: LOG_LEVEL
        credentials:
          secret-env-vars:
            username: SERVICE_USERNAME
            password: SERVICE_PASSWORD

Each option must use exactly one field: ``env-var`` for a non-secret option, or
``secret-env-vars`` for an option declared with ``type: secret``.

Source names must match options declared in ``charmcraft.yaml`` or ``config.yaml`` exactly.
Framework options with environment outputs, such as ``app-secret-key`` and ``flask-debug``,
can be mapped. Options that only configure files or arguments, such as Gunicorn's
``webserver-workers``, cannot. Settings declared only in ``paas-config.yaml``, such as
``port``, are not charm configuration options and cannot be mapping sources.

Destination names are used verbatim, without adding prefixes or changing punctuation or
case. They must be non-empty strings without NUL characters or ``=``. Other characters
are accepted, but the workload and any shell scripts must support the chosen names.

Mappings replace default names rather than add aliases. In Flask, the example emits
``LOG_LEVEL`` instead of ``FLASK_LOG_LEVEL``. Unmapped options retain their existing names.
Another source can still independently generate the old name.

Secret entries
~~~~~~~~~~~~~~

Keys under ``secret-env-vars`` are exact Juju secret content keys. The example renames
the ``username`` and ``password`` entries of the secret configured through ``credentials``.
Unmapped entries retain their default environment variable names.

For ``app-secret-key``, use ``secret-env-vars: {value: SESSION_SECRET}`` to rename the
effective key. This includes the automatically generated key when no secret is configured.

Configured secrets must still pass their original validation; ``app-secret-key`` requires
exactly one entry named ``value``. After validation, if a secret lacks a mapped key,
the charm skips that entry and logs a warning
naming the configuration option, secret content key, and destination, never the secret value.
For framework options exposing a secret as a JSON object, mapped entries are removed from
that object; unmapped entries remain in the original output.

Values and defaults
~~~~~~~~~~~~~~~~~~~

Mappings preserve resolved framework values and their existing encoding. User-defined
strings pass through unchanged; booleans and numbers are JSON-encoded (for example,
``false`` becomes the string ``"false"``). Framework validation and secret resolution
still apply.

Defaults are mapped too. A ``log-level`` default of ``info`` emits ``LOG_LEVEL=info``
without the operator setting the option. Resetting an option uses its default rather
than making it unset.

A source with no value contributes no mapped variable. Any lower-priority destination
value remains unchanged. Empty strings, ``false``, and zero are values and override
lower-priority outputs. Unmapped options retain their existing handling of unset values.

Precedence and collisions
~~~~~~~~~~~~~~~~~~~~~~~~~

Environment variables are applied in this order, from lowest to highest priority:

.. list-table::
   :header-rows: 1

   * - Priority
     - Source
   * - 1
     - Charm configuration and framework-generated settings.
   * - 2
     - Built-in relations and Prometheus metrics.
   * - 3
     - Custom relations, in registration order.
   * - 4
     - Explicit ``config.options`` mappings whose sources have values.

The charm warns when relation outputs replace configuration/framework variables or when
explicit mappings replace existing variables. Warnings name the destination without logging
values; mapping warnings also identify the source option.
Renames use original source values, so swapping two destination names is supported.
Destinations can override framework variables; charm authors must ensure that the workload
still functions.

Validation
----------

The ``paas-config.yaml`` file is validated when the charm initializes to handle a hook.
If validation fails, the hook fails and Juju reports an error. The charm author must
correct the file and repack the charm. Existing applications need the corrected charm
revision; see the `Juju refresh command
<https://documentation.ubuntu.com/juju/3.6/reference/juju-cli/list-of-juju-cli-commands/refresh/>`_
for updating a deployed application.

Common validation errors include:

* Invalid YAML syntax
* Unknown fields
* Missing required fields in nested configuration sections
* Invalid field values
* Unknown source options or mapping fields that do not match an option's declared type
* Duplicate mapping destinations, even when a source is unset
* Ambiguous source option names such as ``foo-bar`` and ``foo_bar``, which the library
  treats identically

Functionality provided
----------------------

The file ``paas-config.yaml`` allows you to:

* Configure the application server port
* Configure the workload metrics endpoint
* Define custom Prometheus scrape targets for metrics collection
* Enable structured framework logs in JSON format
* Rename environment variables generated from config options and secrets

For the detailed configuration schema and detailed examples, see:

.. toctree::
   :maxdepth: 1

   Prometheus configuration <paas-config-prometheus>
   Structured logging configuration <paas-config-structured-logging>
