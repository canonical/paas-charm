# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""The base charm class for all charms."""

import logging
import typing

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

    def check_gevent_package(self) -> bool:
        """Check that gevent is installed.

        Returns:
            True if gevent is installed.
        """
        ddddd = self._container.exec(["pip", "list"])
        list_output = ddddd.wait_output()[0]
        return "gevent" in list_output

    def create_webserver_config(self) -> WebserverConfig:
        """Create a WebserverConfig instance from the charm config.

        Returns:
            A new WebserverConfig instance.

        Raises:
            CharmConfigInvalidError: if the charm configuration is not valid.
        """
        _webserver_config: WebserverConfig = WebserverConfig.from_charm_config(dict(self.config))

        if _webserver_config.worker_class == "sync":
            _webserver_config.worker_class = None

        if _webserver_config.worker_class:
            if "gevent" != typing.cast(str, _webserver_config.worker_class):
                logger.error(
                    "Only 'gevent' and 'sync' are allowed. "
                    "https://documentation.ubuntu.com/rockcraft"
                    "/en/latest/reference/extensions/%s-framework"
                    "/#parts-%s-framework-async-dependencies",
                    self._framework_name,
                    self._framework_name,
                )
                raise CharmConfigInvalidError(
                    "Only 'gevent' and 'sync' are allowed. "
                    "https://documentation.ubuntu.com/rockcraft/en/latest"
                    f"/reference/extensions/{self._framework_name}-"
                    f"framework/#parts-{self._framework_name}-"
                    "framework-async-dependencies"
                )

            if not self.check_gevent_package():
                logger.error(
                    "gunicorn[gevent] must be installed in the rock. "
                    "https://documentation.ubuntu.com/rockcraft"
                    "/en/latest/reference/extensions/%s-framework"
                    "/#parts-%s-framework-async-dependencies",
                    self._framework_name,
                    self._framework_name,
                )
                raise CharmConfigInvalidError(
                    "gunicorn[gevent] must be installed in the rock. "
                    "https://documentation.ubuntu.com/rockcraft/en/latest"
                    f"/reference/extensions/{self._framework_name}-"
                    f"framework/#parts-{self._framework_name}-"
                    "framework-async-dependencies"
                )

        return _webserver_config

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
