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


class TestConfig(FrameworkConfig):
    """Represent Testing builtin configuration values."""

    port: int = Field(alias="port", default=8080, gt=0)
    metrics_port: int | None = Field(alias="metrics-port", default=None, gt=0)
    metrics_path: str | None = Field(alias="metrics-path", default=None, min_length=1)
    app_secret_key: str | None = Field(alias="app-secret-key", default=None, min_length=1)
    model_config = ConfigDict(extra="ignore")


class TestCharm(PaasCharm):
    """Testing charm.

    Attrs:
        framework_config_class: Base class for framework configuration.
    """

    framework_config_class = TestConfig

    def __init__(self, framework: ops.Framework) -> None:
        """Initialize the Go charm.

        Args:
            framework: operator framework.
        """
        super().__init__(framework=framework, framework_name="test")

    @property
    def _workload_config(self) -> WorkloadConfig:
        """Return an WorkloadConfig instance."""
        framework_name = self._framework_name
        base_dir = pathlib.Path("/app")
        framework_config = typing.cast(TestConfig, self.get_framework_config())
        return WorkloadConfig(
            framework=framework_name,
            port=framework_config.port,
            base_dir=base_dir,
            app_dir=base_dir,
            state_dir=self._state_dir,
            service_name=framework_name,
            log_files=[],
            unit_name=self.unit.name,
            metrics_target=f"*:{framework_config.metrics_port}",
            metrics_path=framework_config.metrics_path,
        )

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
