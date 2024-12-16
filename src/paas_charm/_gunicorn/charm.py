# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The base charm class for all charms."""

import logging

from cosl import JujuTopology
from ops.pebble import ExecError, ExecProcess

from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
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
            framework_name=self._framework_name, unit_name=self.unit.name
        )

    def _create_app(self, topology: JujuTopology) -> App:
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
            juju_topology=topology,
        )
