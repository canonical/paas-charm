# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""This module defines the WorloadConfig class which represents configuration for the workload."""

import pathlib

from paas_charm.app import WorkloadConfig
from paas_charm.paas_config import PaasConfig

STATSD_HOST = "localhost:9125"
APPLICATION_LOG_FILE_FMT = "/var/log/{framework}/access.log"
APPLICATION_ERROR_LOG_FILE_FMT = "/var/log/{framework}/error.log"


def create_workload_config(
    framework_name: str,
    unit_name: str,
    state_dir: pathlib.Path,
    paas_config: PaasConfig | None = None,
    tracing_enabled: bool = False,
) -> WorkloadConfig:
    """Create an WorkloadConfig for Gunicorn.

    Args:
        framework_name: framework name.
        unit_name: name of the app unit.
        state_dir: state folder directory.
        paas_config: PaasConfig instance. Uses the schema defaults when omitted.
        tracing_enabled: if True, tracing is enabled.

    Returns:
       new WorkloadConfig
    """
    paas_config = paas_config or PaasConfig()
    metrics_port, metrics_path, configure_metrics = paas_config.metrics_endpoint(
        default_port=paas_config.port, default_path="/metrics"
    )
    base_dir = pathlib.Path(f"/{framework_name}")
    return WorkloadConfig(
        framework=framework_name,
        container_name="app",
        port=paas_config.port,
        base_dir=base_dir,
        app_dir=base_dir / "app",
        state_dir=state_dir,
        service_name=framework_name,
        log_files=[
            pathlib.Path(str.format(APPLICATION_LOG_FILE_FMT, framework=framework_name)),
            pathlib.Path(str.format(APPLICATION_ERROR_LOG_FILE_FMT, framework=framework_name)),
        ],
        metrics_target=f"*:{metrics_port}",
        metrics_path=metrics_path,
        metrics_port=metrics_port,
        configure_metrics=configure_metrics,
        unit_name=unit_name,
        tracing_enabled=tracing_enabled,
        logging_format=paas_config.framework_logging_format,
    )
