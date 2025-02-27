# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go Charm service."""

import pathlib
import typing

import ops
from pydantic import ConfigDict, Field

from paas_charm.app import App, WorkloadConfig
from paas_charm.charm import PaasCharm
from paas_charm.framework import FrameworkConfig

WORKLOAD_CONTAINER_NAME = "app"


class GoConfig(FrameworkConfig):
    """Represent Go builtin configuration values.

    Attrs:
        port: port where the application is listening
        metrics_port: port where the metrics are collected
        metrics_path: path where the metrics are collected
        secret_key: a secret key that will be used for securely signing the session cookie
            and can be used for any other security related needs by your Flask application.
        model_config: Pydantic model configuration.
    """

    port: int = Field(alias="app-port", default=8080, gt=0)
    metrics_port: int | None = Field(alias="metrics-port", default=None, gt=0)
    metrics_path: str | None = Field(alias="metrics-path", default=None, min_length=1)
    secret_key: str | None = Field(alias="app-secret-key", default=None, min_length=1)

    model_config = ConfigDict(extra="ignore")


class Charm(PaasCharm):
    """Go Charm service.

    Attrs:
        framework_config_class: Base class for framework configuration.
    """

    framework_config_class = GoConfig

    def __init__(self, framework: ops.Framework) -> None:
        """Initialize the Go charm.

        Args:
            framework: operator framework.
        """
        super().__init__(framework=framework, framework_name="go")

    @property
    def _workload_config(self) -> WorkloadConfig:
        """Return an WorkloadConfig instance."""
        framework_name = self._framework_name
        base_dir = pathlib.Path("/app")
        framework_config = typing.cast(GoConfig, self.get_framework_config())
        return WorkloadConfig(
            framework=framework_name,
            container_name=WORKLOAD_CONTAINER_NAME,
            port=framework_config.port,
            base_dir=base_dir,
            app_dir=base_dir,
            state_dir=base_dir / "state",
            service_name=framework_name,
            log_files=[],
            metrics_target=f"*:{framework_config.metrics_port}",
            metrics_path=framework_config.metrics_path,
            unit_name=self.unit.name,
        )

    def get_cos_dir(self) -> str:
        """Return the directory with COS related files.

        Returns:
            Return the directory with COS related files.
        """
        return str((pathlib.Path(__file__).parent / "cos").absolute())

    def _create_app(self) -> App:
        """Build a App instance.

        Returns:
            A new App instance.
        """
        charm_state = self._create_charm_state()
        return App(
            container=self._container,
            charm_state=charm_state,
            workload_config=self._workload_config,
            database_migration=self._database_migration,
        )
