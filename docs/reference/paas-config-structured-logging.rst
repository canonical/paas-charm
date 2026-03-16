.. meta::
   :description: Technical details on configuring structured JSON logging. Covers supported frameworks (FastAPI, Flask, Django), behavior, and validation.

.. _ref_paas_config_structured_logging:

Structured logging configuration
================================

Use ``framework_logging_format`` in ``paas-config.yaml`` to enable structured framework logs.

Configuration
-------------

To enable structured logging, write the following snippet in the file ``paas-config.yaml``:

.. code-block:: yaml

   framework_logging_format: json


Supported frameworks
--------------------

``framework_logging_format: json`` is supported for:

* FastAPI (Uvicorn)
* Flask (Gunicorn)
* Django (Gunicorn)

Behavior
--------

When enabled, framework server logs (for example, access logs) are emitted in structured JSON
that follow the OTEL semantic conventions.

Validation
----------

Validation fails when:

* ``framework_logging_format`` is set to an unsupported value.
* ``json`` is requested for a framework that does not support structured framework logging.
