.. _ref_paas_config:

paas-config.yaml
================

The ``paas-config.yaml`` file is an optional configuration file that charm developers
can include in their charm to customize runtime behavior of 12-factor app charms.

The ``paas-config.yaml`` file must be placed in the charm root directory
alongside your ``charmcraft.yaml`` file, and the file has to be included in the packed
charm file.

File structure
--------------

The ``paas-config.yaml`` file uses YAML format and follows a structured schema.
Currently, the file supports the ``prometheus`` top key.

See :ref:`ref_paas_config_prometheus` for detailed Prometheus configuration options.

Validation
----------

The ``paas-config.yaml`` file is validated when the charm is deployed.
If validation fails, the charm will raise an error and stop working. The
``paas-config.yaml`` has to be fixed and the charm packed again.

Common validation errors include:

* Invalid YAML syntax
* Unknown fields
* Missing required fields
* Invalid field values

Functionality provided
----------------------

The file ``paas-config.yaml`` allows you to:

* Define custom Prometheus scrape targets for metrics collection

For the detailed configuration schema and detailed examples, see:

.. toctree::
   :maxdepth: 1

   Prometheus configuration <paas-config-prometheus>
