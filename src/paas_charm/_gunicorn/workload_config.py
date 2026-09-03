# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""This module defines the WorloadConfig class which represents configuration for the workload."""

import pathlib

from paas_charm.app import WorkloadConfig
from paas_charm.paas_config import PaasConfig

STATSD_HOST = "localhost:9125"
APPLICATION_LOG_FILE = "/var/log/app/access.log"
APPLICATION_ERROR_LOG_FILE = "/var/log/app/error.log"
GUNICORN_CONFIG_DIR = "/var/lib/gunicorn"


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
    application_port = paas_config.application_port(default_port=8000)
    metrics_port, metrics_path = paas_config.metrics_endpoint(
        default_port=9102, default_path="/metrics"
    )
    # For Gunicorn, base_dir holds the (mutable) gunicorn.conf.py, kept separate from app_dir
    # (the application source directory) so the two can have different lifecycles/ownership.
    base_dir = pathlib.Path(GUNICORN_CONFIG_DIR)
    app_dir = pathlib.Path("/app")
    return WorkloadConfig(
        framework=framework_name,
        container_name="app",
        port=application_port,
        base_dir=base_dir,
        app_dir=app_dir,
        state_dir=state_dir,
        service_name=framework_name,
        log_files=[
            pathlib.Path(APPLICATION_LOG_FILE),
            pathlib.Path(APPLICATION_ERROR_LOG_FILE),
        ],
        metrics_path=metrics_path,
        metrics_port=metrics_port,
        unit_name=unit_name,
        tracing_enabled=tracing_enabled,
        logging_format=paas_config.framework_logging_format,
    )
