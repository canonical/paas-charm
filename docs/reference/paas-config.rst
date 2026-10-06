.. _ref_paas_config:

paas-config.yaml
================

The ``paas-config.yaml`` file is an optional configuration file that charm developers
can include in their charm to customize runtime behavior of 12-factor app charms.

When used, the ``paas-config.yaml`` file must be placed in the charm root directory
alongside your ``charmcraft.yaml`` file and included in the packed charm file.
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

Charm authors can use ``config.options`` to rename environment variables generated from
user-defined charm configuration options. These entries refer to existing options;
they do not declare new charm configuration options or set their values.

The following example assumes that ``log-level`` and ``api-token`` are declared as
string charm configuration options, and ``credentials`` is declared with ``type: secret``.

.. code-block:: yaml

    config:
      options:
        log-level:
          env-var: LOG_LEVEL
        api-token:
          env-var: API_TOKEN
        credentials:
          secret-env-vars:
            username: SERVICE_USERNAME
            password: SERVICE_PASSWORD

Each listed option must use exactly one of ``env-var`` or ``secret-env-vars``.
Use ``env-var`` for a non-secret option and ``secret-env-vars`` for an option
declared with ``type: secret``. The two fields are mutually exclusive. These
settings belong in ``paas-config.yaml``, not in the option declarations in
``charmcraft.yaml`` or ``config.yaml``.

The source names are the exact option names declared in ``charmcraft.yaml`` or
``config.yaml``. Destination names are complete names used verbatim: the charm does not
add a prefix, replace punctuation, or change their case. Names must be non-empty strings
without NUL characters or ``=``. Dots, hyphens, spaces, and non-ASCII characters are
accepted, although the workload and any shell scripts must support the names you choose.

Only user-defined charm configuration options are supported as sources. Options used
to configure the framework, including ``app-secret-key``, and options under the reserved ``app-``,
``webserver-``, and framework-specific prefixes cannot be mapped. This also applies
to option names used for framework settings, even without a reserved prefix. Some of
these options configure files or command arguments rather than environment variables.
A destination can nevertheless override an environment variable supplied by the framework;
the charm author is responsible for ensuring that the workload still functions.

A mapping renames an output, rather than adding an alias. For example, in Flask,
setting ``env-var: LOG_LEVEL`` under ``log-level`` emits ``LOG_LEVEL`` instead of
``FLASK_LOG_LEVEL``.
Unmapped options retain their existing names and behavior. The old name can still be
present if another source independently generates it.

Secret options
~~~~~~~~~~~~~~

An option declared with ``type: secret`` must use ``secret-env-vars``, even if its secret
contains only one entry. The keys under ``secret-env-vars`` are exact secret content keys.
For example, the ``credentials`` mapping above reads the Juju secret configured through
that option and renames its ``username`` and ``password`` entries separately. Unmapped
secret entries retain their default environment variable names.

If a configured Juju secret lacks a mapped secret content key, the charm skips that
mapping and logs a warning containing the charm configuration option, secret content key,
and destination environment variable names, never the secret value. This behavior also
applies when secret content changes on rotation.

Defaults and unset options
~~~~~~~~~~~~~~~~~~~~~~~~~~

Declared charm configuration defaults are mapped too. For example, if ``log-level``
has the default ``info``, the mapping emits ``LOG_LEVEL=info`` even when the operator
has not set the option. Resetting the option to its default does not make it unset.

If a mapped charm configuration option has no value, including no configured Juju
secret for an option of type ``secret``, it contributes no mapped environment variable.
An existing lower-priority variable at the destination remains unchanged. Empty strings,
``false``, and zero are actual values and do override lower-priority outputs.

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
     - Environment variables from charm configuration options and framework settings,
       including metrics, proxies, base URL, and peer information.
   * - 2
     - Environment variables for built-in relations and Prometheus metrics.
   * - 3
     - Explicit ``config.options`` mappings.

Among variables at priority 1, framework settings override user-defined charm configuration
options; environment variables for metrics, connections, proxies, and peers are added afterward.
The generated application secret key is a fallback, inserted only if its name is absent.
Framework-specific adjustments are completed before relation variables are merged.
Explicit application and metrics settings elsewhere in ``paas-config.yaml`` retain
their existing precedence over corresponding charm configuration options.

Environment variables for built-in relations and Prometheus metrics are merged in
this order: OpenFGA, RabbitMQ, Valkey, S3,
databases, SAML, SMTP, tracing, Prometheus, then OAuth. Later generators win when their
names collide. Database outputs are merged in their existing iteration order; in
particular, multiple Spring Boot databases can generate the same ``spring.datasource.*``
properties.

When an environment variable for a relation or Prometheus metrics replaces an environment
variable from a charm configuration option or a framework setting, the charm logs a warning
naming the destination without logging its value.

Explicit mappings are applied last and take precedence over other environment variables,
including framework-specific logging settings. When a mapped destination replaces an
existing variable, the charm logs a warning identifying the charm configuration option
and destination, without logging values. A newly connected optional relation does not cause a
collision error: the mapped value still wins. Renames are resolved together, so swapping
two source variables' names is supported.

Two explicit sources cannot target the same destination, even if one is currently unset.
Unknown source options, use of the wrong field for an option's declared type, invalid destination
names, and duplicate explicit YAML mapping keys are also errors. Duplicate explicit
keys are rejected even within mappings used as YAML merge sources. YAML merges and
explicit overrides of merged values remain supported.

These are charm-authoring errors that cause a hook failure, reported by Juju as an error,
rather than asking the operator to resolve them through charm configuration changes.

The library treats hyphens and underscores identically in charm configuration option
names internally. Options such as ``foo-bar`` and ``foo_bar`` therefore cannot be
distinguished as mapping sources and are rejected.

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
