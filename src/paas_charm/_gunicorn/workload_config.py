# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""This module defines the WorloadConfig class which represents configuration for the workload."""

import pathlib

from paas_charm.app import WorkloadConfig

STATSD_HOST = "localhost:9125"
APPLICATION_LOG_FILE_FMT = "/var/log/{framework}/access.log"
APPLICATION_ERROR_LOG_FILE_FMT = "/var/log/{framework}/error.log"


def create_workload_config(
    framework_name: str, unit_name: str, tracing_enabled: bool = False
) -> WorkloadConfig:
    """Create an WorkloadConfig for Gunicorn.

    Args:
        framework_name: framework name.
        unit_name: name of the app unit.
        tracing_enabled: if True, tracing is enabled.

    Returns:
       new WorkloadConfig
    """
    base_dir = pathlib.Path(f"/{framework_name}")
    # It is  fine to use the tmp directory here as it is only used for storing the state
    # of the application. State only supposed to live within the lifecycle of the container.
    state_dir = pathlib.Path(f"/tmp/{framework_name}/state")  # nosec: B108
    return WorkloadConfig(
        framework=framework_name,
        container_name=f"{framework_name}-app",
        port=8000,
        base_dir=base_dir,
        app_dir=base_dir / "app",
        state_dir=state_dir,
        service_name=framework_name,
        log_files=[
            pathlib.Path(str.format(APPLICATION_LOG_FILE_FMT, framework=framework_name)),
            pathlib.Path(str.format(APPLICATION_ERROR_LOG_FILE_FMT, framework=framework_name)),
        ],
        metrics_target="*:9102",
        unit_name=unit_name,
        tracing_enabled=tracing_enabled,
    )
