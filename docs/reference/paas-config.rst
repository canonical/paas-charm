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
``prometheus``, ``framework_logging_format``, and ``env`` top-level keys.

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

Charm authors can use ``env.config`` to rename environment variables generated from
user-defined charm configuration options:

.. code-block:: yaml

    env:
      config:
        log-level: LOG_LEVEL
        api-token: API_TOKEN
        credentials:
          username: SERVICE_USERNAME
          password: SERVICE_PASSWORD

The source names are the exact option names declared in ``charmcraft.yaml`` or
``config.yaml``. Destination names are complete names used verbatim: the charm does not
add a prefix, replace punctuation, or change their case. Names must be non-empty strings
without NUL characters or ``=``. Dots, hyphens, spaces, and non-ASCII characters are
accepted, although the workload and any shell scripts must support the names you choose.

When relation output overwrites an ordinary configuration or framework environment
variable, a warning names the destination but does not include its value.

Only user-defined configuration options are supported as sources. Framework-owned
options, including ``app-secret-key``, and options under the reserved ``app-``,
``webserver-``, and framework-specific prefixes cannot be mapped. This also applies
to option names that match a framework configuration field or its alias, even
without a reserved prefix. Some of these options
configure files or command arguments rather than environment variables. A destination
can nevertheless override a framework-owned environment variable; the charm author is
responsible for ensuring that the workload still functions.

A mapping renames an output, rather than adding an alias. For example, in Flask,
``log-level: LOG_LEVEL`` emits ``LOG_LEVEL`` instead of ``FLASK_LOG_LEVEL``.
Unmapped options retain their existing names and behavior. The old name can still be
present if another source independently generates it.

Secret options
~~~~~~~~~~~~~~

An option declared with ``type: secret`` must use a nested mapping, even if its secret
contains only one entry. The nested source names are exact secret content keys.
For example, the ``credentials`` mapping above reads the Juju secret configured through
that option and renames its ``username`` and ``password`` entries separately. Unmapped
secret entries retain their default environment variable names.

An unset mapped option or an entirely unset secret contributes no mapped output.
An existing lower-priority variable at the destination remains unchanged. Empty strings,
``false``, and zero are actual values and do override lower-priority outputs.
If a configured secret lacks a mapped entry, the charm skips that entry and logs a
warning containing the option and entry names, never the secret value. This behavior
also applies when secret content changes on rotation.

Value formatting
~~~~~~~~~~~~~~~~

Mappings change names only. Existing validation, secret resolution, and value encoding
remain in effect. Strings are passed through unchanged; booleans and numbers are
JSON-encoded (for example, ``false`` becomes the string ``"false"``).
No value translation, templates, or formatting settings are supported by this section.
The omission of unset values applies to mapped sources only; unmapped sources retain
their existing handling of unset values.

Precedence and collisions
~~~~~~~~~~~~~~~~~~~~~~~~~

The environment is assembled in the following order, from lowest to highest priority:

.. list-table::
   :header-rows: 1

   * - Priority
     - Source
   * - 1
     - Ordinary config and library-generated variables, including framework-specific
       settings, metrics, proxies, base URL, and peer information.
   * - 2
     - Built-in relation variables.
   * - 3
     - Custom relation variables, when custom-relation support is available.
   * - 4
     - Explicit ``env.config`` mappings.

Custom-relation support is being introduced separately. Its intended position is after
built-in relations, with later entries in the custom relation list taking precedence.
It is not enabled by ``env.config``.

Within the first layer, framework config overrides ordinary user-defined config;
workload metrics and generated connection/proxy/peer information are added afterward.
The generated application secret key is a fallback, inserted only if its name is absent.
Framework-specific adjustments are completed before relation variables are merged.
Explicit application and metrics settings elsewhere in ``paas-config.yaml`` retain
their existing precedence over corresponding Juju framework config values.

Built-in relation generators are merged in this order: OpenFGA, RabbitMQ, Valkey, S3,
databases, SAML, SMTP, tracing, Prometheus, then OAuth. Later generators win when their
names collide. Database outputs are merged in their existing iteration order; in
particular, multiple Spring Boot databases can generate the same ``spring.datasource.*``
properties.

Explicit mappings are applied last and take precedence over every generated output,
including framework-specific logging settings. When a mapped destination replaces an
existing variable, the charm logs a warning identifying the config source and destination,
without logging values. A newly connected optional integration does not cause a
collision error: the mapped value still wins. Renames are resolved together, so swapping
two source variables' names is supported.

Two explicit sources cannot target the same destination, even if one is currently unset.
Unknown source options, incorrect scalar/secret mapping shapes, invalid destination
names, and duplicate YAML keys are also errors. These are charm-authoring errors:
the charm enters error state, rather than asking the operator to resolve them through
Juju configuration.

Sources whose names become identical after the library's hyphen-to-underscore
normalization (such as ``foo-bar`` and ``foo_bar``) cannot be mapped unambiguously
and are rejected.

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
* Rename environment variables generated from user-defined config options and secrets

For the detailed configuration schema and detailed examples, see:

.. toctree::
   :maxdepth: 1

   Prometheus configuration <paas-config-prometheus>
   Structured logging configuration <paas-config-structured-logging>
