# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the FastAPIApp class to manage the FastAPI/Uvicorn application."""

import importlib.resources
import logging
import pathlib

import ops

from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState
from paas_charm.database_migration import DatabaseMigration
from paas_charm.paas_config import LoggingFormat

logger = logging.getLogger(__name__)

# The directory where logging files will be pushed inside the container.
# The logging related files are pushed again if the container is recreated, and must
# be in a place where the pebble user (that could be non-root) has write permissions.
_OPT_DIR = pathlib.PurePosixPath("/tmp/fastapi/log_config")  # nosec: B108
_HANDLER_FILE = "uvicorn_log_handler.py"
_CONFIG_FILE = "uvicorn-log-config.json"


class FastAPIApp(App):
    """FastAPI/Uvicorn application manager.

    Extends the base :class:`~paas_charm.app.App` with structured JSON logging
    support.  When ``workload_config.logging_format == LoggingFormat.JSON`` the charm pushes
    a JSON formatter module and a uvicorn ``dictConfig`` logging configuration
    file into ``/tmp/fastapi/log_config/`` inside the container, then activates them
    via ``PYTHONPATH`` and ``UVICORN_LOG_CONFIG`` environment variables.
    """

    def __init__(
        self,
        *,
        container: ops.Container,
        charm_state: CharmState,
        workload_config: WorkloadConfig,
        database_migration: DatabaseMigration,
    ):
        """Construct the FastAPIApp instance.

        Args:
            container: The FastAPI application container.
            charm_state: The state of the charm.
            workload_config: Workload configuration including optional logging_format.
            database_migration: The database migration manager object.
        """
        super().__init__(
            container=container,
            charm_state=charm_state,
            workload_config=workload_config,
            database_migration=database_migration,
            framework_config_prefix="",
        )

    def _prepare_service_for_restart(self) -> None:
        """Push structured logging files to the container when JSON logging is configured."""
        if self._workload_config.logging_format != LoggingFormat.JSON:
            return
        self._container.make_dir(
            str(_OPT_DIR),
            make_parents=True,
            user=self._workload_config.user,
            group=self._workload_config.group,
        )
        for filename in (_HANDLER_FILE, _CONFIG_FILE):
            content = _read_template(filename)
            self._container.push(
                str(_OPT_DIR / filename),
                content,
                user=self._workload_config.user,
                group=self._workload_config.group,
            )
            logger.debug("Pushed %s to container", filename)

    def gen_environment(self) -> dict[str, str]:
        """Return the application environment, adding logging vars when JSON is configured.

        Returns:
            A dictionary of environment variable name → value.
        """
        env = super().gen_environment()
        if self._workload_config.logging_format == LoggingFormat.JSON:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{_OPT_DIR}:{existing}" if existing else str(_OPT_DIR)
            env["UVICORN_LOG_CONFIG"] = str(_OPT_DIR / _CONFIG_FILE)
        return env


def _read_template(filename: str) -> str:
    """Read a file from the fastapi templates directory bundled with paas_charm.

    Args:
        filename: Bare filename to read from ``templates/fastapi/``.

    Returns:
        The file contents as a string.
    """
    package = importlib.resources.files("paas_charm") / "templates" / "fastapi"
    return (package / filename).read_text(encoding="utf-8")
