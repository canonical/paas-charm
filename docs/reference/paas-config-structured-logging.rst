.. _ref_paas_config_structured_logging:

Structured logging configuration
================================

Use ``framework_logging_format`` in ``paas-config.yaml`` to enable structured framework logs.

Configuration
-------------

To enable structured logging, set:

.. code-block:: yaml

   framework_logging_format: json

This is a charm-developer setting in ``paas-config.yaml`` (build-time packaging input),
not a Juju runtime config option.

Supported frameworks
--------------------

``framework_logging_format: json`` is supported for:

* FastAPI (Uvicorn)
* Flask (Gunicorn)
* Django (Gunicorn)

Behavior
--------

When enabled, framework server logs (for example, access logs) are emitted in structured JSON.
The emitted fields follow an OTEL-style shape used by the charm logging pipeline.

Validation
----------

Validation fails when:

* ``framework_logging_format`` is set to an unsupported value.
* ``json`` is requested for a framework that does not support structured framework logging.

TODO ON LOGGING IN GENERAL
- USE STDOUT/STDERR, NOT FILES.
- PAAS-CHARM ONLY CHANGES FRAMEWORK LOGGING THAT CANNOT BE EASILY CHANGED FROM APP CODE.
