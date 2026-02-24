.. _how_to_add_custom_cos_assets:

Custom COS dashboards and alert rules
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


Add alert rules
---------------

Custom alert rules are loaded from:

* ``cos_custom/prometheus_alert_rules/`` for Prometheus rules
* ``cos_custom/loki_alert_rules/`` for Loki rules

The alert rules use these relation interfaces:

* ``metrics-endpoint`` (Prometheus)
* ``logging`` (Loki)

A minimal alert rule file looks like:

.. code-block:: yaml

   alert: AppTargetMissing
   expr: up == 0
   for: 1m
   labels:
     severity: critical
   annotations:
     summary: Target missing (instance {{ $labels.instance }})
     description: Prometheus target disappeared.

Save the rule as a ``.rule`` file, for example:

* ``cos_custom/prometheus_alert_rules/app.rule``
* ``cos_custom/loki_alert_rules/app.rule``

When the charm starts, custom assets are merged with the default assets.

For rule syntax and advanced examples, see the official documentation:

* `Prometheus alerting rules <https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/>`_
* `Loki alerting rules <https://grafana.com/docs/loki/latest/alert/>`_
