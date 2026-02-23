.. _how_to_custom_cos_assets:

Provide custom COS dashboards and alert rules
=============================================

The 12-factor charms ship with default observability assets used by the
Grafana, Loki, and Prometheus integrations (dashboards and alert rules).

You can add your own assets by placing a ``cos_custom/``
directory at the root of your charm source tree.

The default assets will be merged with the custom assets at runtime.

Directory layout
----------------

Create the following directory structure in your charm project:

.. code-block:: text

   cos_custom/
     grafana_dashboards/
     loki_alert_rules/
     prometheus_alert_rules/

.. note::

    Only the three subdirectories above are allowed.
    Any other subdirectory name is considered invalid.
