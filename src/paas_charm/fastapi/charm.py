# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""FastAPI Charm service."""

import pathlib
import typing

import ops
from pydantic import ConfigDict, Field

from paas_charm.app import App, WorkloadConfig
from paas_charm.charm import PaasCharm
from paas_charm.fastapi.app import FastAPIApp
from paas_charm.framework import FrameworkConfig


class FastAPIConfig(FrameworkConfig):
    """Represent FastAPI builtin configuration values.

    Attrs:
        uvicorn_port: port where the application is listening
        uvicorn_host: The uvicorn host name or ip address where uvicorn is listening
        web_concurrency: number of workers for uvicorn
        uvicorn_log_level: uvicorn log level
        app_secret_key: a secret key that will be used for securely signing the session cookie
            and can be used for any other security related needs by your Flask application.
        model_config: Pydantic model configuration.
    """

    uvicorn_port: int = Field(alias="webserver-port", default=8080, gt=0)
    uvicorn_host: str = Field(alias="webserver-host", default="0.0.0.0")  # nosec
    web_concurrency: int = Field(alias="webserver-workers", default=1, gt=0)
    uvicorn_log_level: typing.Literal["critical", "error", "warning", "info", "debug", "trace"] = (
        Field(alias="webserver-log-level", default="info")
    )
    app_secret_key: str | None = Field(alias="app-secret-key", default=None, min_length=1)

    model_config = ConfigDict(extra="ignore")


class Charm(PaasCharm):
    """FastAPI Charm service.

    Attrs:
        framework_config_class: Base class for framework configuration.
        paas_config_framework_fields: Mapping from framework fields to paas-config fields.
    """

    framework_config_class = FastAPIConfig
    paas_config_framework_fields = {
        "uvicorn_port": "port",
    }

    def __init__(self, framework: ops.Framework) -> None:
        """Initialize the FastAPI charm.

        Args:
            framework: operator framework.
        """
        super().__init__(framework=framework, framework_name="fastapi")

    @property
    def _workload_config(self) -> WorkloadConfig:
        """Return an WorkloadConfig instance."""
        framework_name = self._framework_name
        base_dir = pathlib.Path("/app")
        framework_config = typing.cast(FastAPIConfig, self.get_framework_config())
        metrics_port, metrics_path = self._paas_config.metrics_endpoint(
            default_port=8080, default_path="/metrics"
        )
        return WorkloadConfig(
            framework=framework_name,
            port=framework_config.uvicorn_port,
            base_dir=base_dir,
            app_dir=base_dir,
            state_dir=self._state_dir,
            service_name=framework_name,
            log_files=[],
            metrics_path=metrics_path,
            metrics_port=metrics_port,
            unit_name=self.unit.name,
            logging_format=self._paas_config.framework_logging_format,
        )

    def _create_app(self) -> App:
        """Build a App instance.

        Returns:
            A new App instance.
        """
        charm_state = self._create_charm_state()
        return FastAPIApp(
            container=self._container,
            charm_state=charm_state,
            workload_config=self._workload_config,
            database_migration=self._database_migration,
        )
