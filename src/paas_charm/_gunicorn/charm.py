# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""The base charm class for all charms."""

import logging

from ops.pebble import ExecError, ExecProcess

from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig, WorkerClassEnum
from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm._gunicorn.wsgi_app import WsgiApp
from paas_charm.app import App, WorkloadConfig
from paas_charm.charm import PaasCharm
from paas_charm.exceptions import CharmConfigInvalidError

logger = logging.getLogger(__name__)


class GunicornBase(PaasCharm):
    """Gunicorn-based charm service mixin."""

    @property
    def _workload_config(self) -> WorkloadConfig:
        """Return a WorkloadConfig instance."""
        return create_workload_config(
            framework_name=self._framework_name,
            unit_name=self.unit.name,
            tracing_enabled=bool(self._tracing and self._tracing.is_ready()),
        )

    def create_webserver_config(self) -> WebserverConfig:
        """Validate worker_class and create a WebserverConfig instance from the charm config.

        Returns:
            A validated WebserverConfig instance.

        Raises:
            CharmConfigInvalidError: if the charm configuration is not valid.
        """
        webserver_config: WebserverConfig = WebserverConfig.from_charm_config(dict(self.config))
        if not webserver_config.worker_class:
            return webserver_config

        doc_link = f"https://bit.ly/{self._framework_name}-async-doc"

        worker_class = WorkerClassEnum.SYNC
        try:
            worker_class = WorkerClassEnum(webserver_config.worker_class)
        except ValueError as exc:
            logger.error(
                "Only 'gevent' and 'sync' are allowed. %s",
                doc_link,
            )
            raise CharmConfigInvalidError(
                f"Only 'gevent' and 'sync' are allowed. {doc_link}"
            ) from exc

        # If the worker_class = sync is the default.
        if worker_class is WorkerClassEnum.SYNC:
            return webserver_config

        if not self._check_gevent_package():
            logger.error(
                "gunicorn[gevent] must be installed in the rock. %s",
                doc_link,
            )
            raise CharmConfigInvalidError(
                f"gunicorn[gevent] must be installed in the rock. {doc_link}"
            )

        return webserver_config

    def _create_app(self) -> App:
        """Build an App instance for the Gunicorn based charm.

        Returns:
            A new App instance.
        """
        charm_state = self._create_charm_state()

        webserver = GunicornWebserver(
            webserver_config=self.create_webserver_config(),
            workload_config=self._workload_config,
            container=self.unit.get_container(self._workload_config.container_name),
        )

        return WsgiApp(
            container=self._container,
            charm_state=charm_state,
            workload_config=self._workload_config,
            webserver=webserver,
            database_migration=self._database_migration,
        )

    def _check_gevent_package(self) -> bool:
        """Check that gevent is installed.

        Returns:
            True if gevent is installed.
        """
        try:
            check_gevent_process: ExecProcess = self._container.exec(
                ["python3", "-c", "import gevent"]
            )
            check_gevent_process.wait_output()
            return True
        except ExecError as cmd_error:
            logger.warning("gunicorn[gevent] install check failed: %s", cmd_error)
            return False
