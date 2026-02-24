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


Add dashboards
--------------

Custom dashboards are loaded from ``cos_custom/grafana_dashboards/``.

Save each dashboard as a ``.json`` file, for example:

* ``cos_custom/grafana_dashboards/app-overview.json``

When creating a dashboard, use variables for your datasources and name them
``prometheusds`` and ``lokids``. You can make use of the Juju topology variables
(``$juju_model``, ``$juju_model_uuid``, ``$juju_application``, ``$juju_unit``).

For dashboard authoring guidance and JSON structure reference, see:

* `Build dashboards <https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/>`_
* `Dashboard JSON model <https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/>`_
* `Grafana dashboard library documentation <https://charmhub.io/grafana-k8s/libraries/grafana_dashboard>`_.


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

Prometheus charm libraries document these formats in the
`prometheus_scrape <https://charmhub.io/prometheus-k8s/libraries/prometheus_scrape>`_ reference.
Loki alert rules must include the ``%%juju_topology%%`` placeholder
(as described in the `loki_push_api library <https://charmhub.io/loki-k8s/libraries/loki_push_api>`_).

Save the rule as a ``.rule`` / ``.rules`` / ``.yml`` / ``.yaml`` file, for example:

* ``cos_custom/prometheus_alert_rules/app.rule``
* ``cos_custom/loki_alert_rules/app.rule``

When the charm starts, custom assets are merged with the default assets.

For rule syntax and advanced examples, see the official documentation:

* `Prometheus alerting rules <https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/>`_
* `Loki alerting rules <https://grafana.com/docs/loki/latest/alert/>`_
