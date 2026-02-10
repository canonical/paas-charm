# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the Observability class to represent the observability stack for charms."""

import logging
import os.path
import pathlib
import typing

import ops
from charms.grafana_k8s.v0.grafana_dashboard import GrafanaDashboardProvider
from charms.prometheus_k8s.v0.prometheus_scrape import MetricsEndpointProvider

from paas_charm.app import SCHEDULER_UNIT_NUMBER
from paas_charm.paas_config import PrometheusConfig
from paas_charm.utils import build_k8s_unit_fqdn, enable_pebble_log_forwarding

logger = logging.getLogger(__name__)


class Observability(ops.Object):
    """A class representing the observability stack for charm managed application."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        charm: ops.CharmBase,
        container_name: str,
        cos_dir: str,
        log_files: list[pathlib.Path],
        metrics_target: str | None,
        metrics_path: str | None,
        prometheus_config: PrometheusConfig | None = None,
    ):
        """Initialize a new instance of the Observability class.

        Args:
            charm: The charm object that the Observability instance belongs to.
            container_name: The name of the application container.
            cos_dir: The directories containing the grafana_dashboards, loki_alert_rules and
                prometheus_alert_rules.
            log_files: List of files to monitor.
            metrics_target: Target to scrape for metrics.
            metrics_path: Path to scrape for metrics.
            prometheus_config: Custom Prometheus configuration from paas-config.yaml.
        """
        super().__init__(charm, "observability")
        self._charm = charm
        jobs = build_prometheus_jobs(
            metrics_target, metrics_path, prometheus_config, charm.app.name, charm.model.name
        )
        self._metrics_endpoint = MetricsEndpointProvider(
            charm,
            alert_rules_path=os.path.join(cos_dir, "prometheus_alert_rules"),
            jobs=jobs,
            relation_name="metrics-endpoint",
            refresh_event=[charm.on.config_changed, charm.on[container_name].pebble_ready],
        )
        # The charm isn't necessarily bundled with charms.loki_k8s.v1
        # Dynamically switches between two versions here.
        if enable_pebble_log_forwarding():
            # ignore "import outside toplevel" linting error
            import charms.loki_k8s.v1.loki_push_api  # pylint: disable=import-outside-toplevel

            self._logging = charms.loki_k8s.v1.loki_push_api.LogForwarder(
                charm, relation_name="logging"
            )
        else:
            try:
                # ignore "import outside toplevel" linting error
                import charms.loki_k8s.v0.loki_push_api  # pylint: disable=import-outside-toplevel

                self._logging = charms.loki_k8s.v0.loki_push_api.LogProxyConsumer(
                    charm,
                    alert_rules_path=os.path.join(cos_dir, "loki_alert_rules"),
                    container_name=container_name,
                    log_files=[str(log_file) for log_file in log_files],
                    relation_name="logging",
                )
            except ImportError:
                # ignore "import outside toplevel" linting error
                import charms.loki_k8s.v1.loki_push_api  # pylint: disable=import-outside-toplevel

                self._logging = charms.loki_k8s.v1.loki_push_api.LogProxyConsumer(
                    charm,
                    logs_scheme={
                        container_name: {
                            "log-files": [str(log_file) for log_file in log_files],
                        },
                    },
                    relation_name="logging",
                )

        self._grafana_dashboards = GrafanaDashboardProvider(
            charm,
            dashboards_path=os.path.join(cos_dir, "grafana_dashboards"),
            relation_name="grafana-dashboard",
        )


def build_prometheus_jobs(
    metrics_target: str | None,
    metrics_path: str | None,
    prometheus_config: PrometheusConfig | None,
    app_name: str,
    model_name: str,
) -> list[dict[str, typing.Any]]:
    """Build Prometheus scrape jobs list from framework defaults and custom config.

    Args:
        metrics_target: Default framework metrics target (e.g., "*:8000").
        metrics_path: Default framework metrics path (e.g., "/metrics").
        prometheus_config: Custom Prometheus configuration from paas-config.yaml.
        app_name: Application name for @scheduler resolution.
        model_name: Juju model name for @scheduler resolution.

    Returns:
        List of Prometheus job configurations (empty list if no jobs are configured).
    """
    jobs: list[dict[str, typing.Any]] = []

    # Add default framework job if configured. The library adds a default job_name.
    if metrics_path and metrics_target:
        resolved_target = _resolve_scheduler_placeholder(app_name, model_name, metrics_target)
        jobs.append(
            {"metrics_path": metrics_path, "static_configs": [{"targets": [resolved_target]}]}
        )

    # Add custom jobs from paas-config.yaml
    if prometheus_config and prometheus_config.scrape_configs:
        for scrape_config in prometheus_config.scrape_configs:
            jobs.append(
                {
                    "job_name": scrape_config.job_name,
                    "metrics_path": scrape_config.metrics_path,
                    "static_configs": [
                        (
                            {
                                "targets": [
                                    _resolve_scheduler_placeholder(app_name, model_name, target)
                                    for target in sc.targets
                                ],
                                "labels": sc.labels,
                            }
                            if sc.labels
                            else {
                                "targets": [
                                    _resolve_scheduler_placeholder(app_name, model_name, target)
                                    for target in sc.targets
                                ]
                            }
                        )
                        for sc in scrape_config.static_configs
                    ],
                }
            )

    return jobs


def _resolve_scheduler_placeholder(app_name: str, model_name: str, target: str) -> str:
    """Replace @scheduler placeholder with scheduler unit FQDN.

    Args:
        app_name: Application name (e.g., "flask-app").
        model_name: Juju model name (e.g., "my-model").
        target: Target string possibly containing @scheduler placeholder.

    Returns:
        Target with @scheduler replaced by scheduler unit's Kubernetes DNS FQDN,
        or unchanged target if no @scheduler placeholder present.

    Note:
        This uses Kubernetes DNS service discovery. An alternative could be to use the
        pod IP directly from a peer relation.
    """
    if target.startswith("@scheduler:"):
        port = target.split(":", 1)[1]
        scheduler_fqdn = build_k8s_unit_fqdn(app_name, SCHEDULER_UNIT_NUMBER, model_name)
        return f"{scheduler_fqdn}:{port}"
    return target
