# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the WsgiApp class to represent the WSGI application."""

import logging
import shlex

import ops

from paas_charm._gunicorn.webserver import GunicornWebserver
from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState
from paas_charm.database_migration import DatabaseMigration
from paas_charm.exceptions import CharmConfigInvalidError

logger = logging.getLogger(__name__)


class WsgiApp(App):
    """WSGI application manager."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        container: ops.Container,
        charm_state: CharmState,
        workload_config: WorkloadConfig,
        database_migration: DatabaseMigration,
        webserver: GunicornWebserver,
    ):
        """Construct the WsgiApp instance.

        Args:
            container: The WSGI application container.
            charm_state: The state of the charm.
            workload_config: The state of the workload that the WsgiApp belongs to.
            database_migration: The database migration manager object.
            webserver: The webserver manager object.

        Raises:
            CharmConfigInvalidError: When the worker-class config option is set but
              the `-k` worker-class selector argument is not in the service command.
        """
        super().__init__(
            container=container,
            charm_state=charm_state,
            workload_config=workload_config,
            database_migration=database_migration,
            configuration_prefix=f"{workload_config.framework.upper()}_",
            framework_config_prefix=f"{workload_config.framework.upper()}_",
        )
        self._webserver = webserver

        if not webserver._webserver_config.worker_class:
            return

        current_command = shlex.split(
            self._app_layer()["services"][self._workload_config.framework]["command"]
        )
        try:
            k_index = current_command.index("-k")
        except ValueError as exc:
            raise CharmConfigInvalidError(
                "Worker class is set through `juju config` but the"
                " `-k` worker class argument is not in the service command."
            ) from exc
        worker_class_index = k_index + 1 if current_command[k_index + 1] != "[" else k_index + 2
        if webserver._webserver_config.worker_class == current_command[worker_class_index]:
            return

        new_command = current_command
        new_command[worker_class_index] = webserver._webserver_config.worker_class
        self._alternate_service_command = " ".join(new_command)

    def _prepare_service_for_restart(self) -> None:
        """Specific framework operations before restarting the service."""
        service_name = self._workload_config.service_name
        is_webserver_running = self._container.get_service(service_name).is_running()
        command = self._app_layer()["services"][self._workload_config.framework]["command"]
        self._webserver.update_config(
            environment=self.gen_environment(),
            is_webserver_running=is_webserver_running,
            command=command,
        )
