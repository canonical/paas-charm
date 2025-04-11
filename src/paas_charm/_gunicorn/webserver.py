# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the GunicornWebserver class to represent the gunicorn server."""
import dataclasses
import datetime
import logging
import pathlib
import shlex
import signal
import typing
from enum import Enum

import jinja2
import ops
from ops.pebble import ExecError, PathError

from paas_charm._gunicorn.workload_config import (
    APPLICATION_ERROR_LOG_FILE_FMT,
    APPLICATION_LOG_FILE_FMT,
    STATSD_HOST,
)
from paas_charm.app import WorkloadConfig
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.utils import enable_pebble_log_forwarding

logger = logging.getLogger(__name__)


class WorkerClassEnum(str, Enum):
    """Enumeration class defining async modes.

    Attributes:
        SYNC (str): String representation of worker class.
        GEVENT (Enum): Enumeration representation of worker class.

    Args:
        str (str): String representation of worker class.
        Enum (Enum): Enumeration representation of worker class.
    """

    SYNC = "sync"
    GEVENT = "gevent"


@dataclasses.dataclass
class WebserverConfig:
    """Represent the configuration values for a web server.

    Attributes:
        workers: The number of workers to use for the web server, or None if not specified.
        worker_class: The method of workers to use for the web server, or sync if not specified.
        threads: The number of threads per worker to use for the web server,
            or None if not specified.
        keepalive: The time to wait for requests on a Keep-Alive connection,
            or None if not specified.
        timeout: The request silence timeout for the web server, or None if not specified.
    """

    workers: int | None = None
    worker_class: WorkerClassEnum | None = WorkerClassEnum.SYNC
    threads: int | None = None
    keepalive: datetime.timedelta | None = None
    timeout: datetime.timedelta | None = None

    def items(
        self,
    ) -> typing.Iterable[tuple[str, str | WorkerClassEnum | int | datetime.timedelta | None]]:
        """Return the dataclass values as an iterable of the key-value pairs.

        Returns:
            An iterable of the key-value pairs.
        """
        return {
            "workers": self.workers,
            "worker_class": self.worker_class,
            "threads": self.threads,
            "keepalive": self.keepalive,
            "timeout": self.timeout,
        }.items()

    @classmethod
    def from_charm_config(
        cls, config: dict[str, WorkerClassEnum | int | float | str | bool]
    ) -> "WebserverConfig":
        """Create a WebserverConfig object from a charm state object.

        Args:
            config: The charm config as a dict.

        Returns:
            A WebserverConfig object.
        """
        keepalive = config.get("webserver-keepalive")
        timeout = config.get("webserver-timeout")
        workers = config.get("webserver-workers")
        worker_class = config.get("webserver-worker-class")
        threads = config.get("webserver-threads")
        return cls(
            workers=int(typing.cast(str, workers)) if workers is not None else None,
            worker_class=(
                typing.cast(WorkerClassEnum, worker_class) if worker_class is not None else None
            ),
            threads=int(typing.cast(str, threads)) if threads is not None else None,
            keepalive=(
                datetime.timedelta(seconds=int(keepalive)) if keepalive is not None else None
            ),
            timeout=(datetime.timedelta(seconds=int(timeout)) if timeout is not None else None),
        )


class GunicornWebserver:  # pylint: disable=too-few-public-methods
    """A class representing a Gunicorn web server."""

    def __init__(
        self,
        webserver_config: WebserverConfig,
        workload_config: WorkloadConfig,
        container: ops.Container,
    ):
        """Initialize a new instance of the GunicornWebserver class.

        Args:
            webserver_config: the Gunicorn webserver configuration.
            workload_config: The state of the workload that the GunicornWebserver belongs to.
            container: The WSGI application container in this charm unit.
        """
        self._webserver_config = webserver_config
        self._workload_config = workload_config
        self._container = container
        self._reload_signal = signal.SIGHUP

    @property
    def _config(self) -> str:
        """Generate the content of the Gunicorn configuration file based on charm states.

        Returns:
            The content of the Gunicorn configuration file.
        """
        config_entries = {}
        for setting, setting_value in self._webserver_config.items():
            setting_value = typing.cast(
                None | str | WorkerClassEnum | int | datetime.timedelta, setting_value
            )
            if setting == "worker_class":
                continue
            if setting_value is None:
                continue
            config_entries[setting] = (
                setting_value
                if isinstance(setting_value, (int, str))
                else int(setting_value.total_seconds())
            )
        if enable_pebble_log_forwarding():
            access_log = "-"
            error_log = "-"
        else:
            access_log = str(
                APPLICATION_LOG_FILE_FMT.format(framework=self._workload_config.framework)
            )
            error_log = str(
                APPLICATION_ERROR_LOG_FILE_FMT.format(framework=self._workload_config.framework)
            )

        jinja_environment = jinja2.Environment(
            loader=jinja2.PackageLoader("paas_charm", "templates"), autoescape=True
        )
        config = jinja_environment.get_template("gunicorn.conf.py.j2").render(
            workload_port=self._workload_config.port,
            workload_app_dir=str(self._workload_config.app_dir),
            access_log=access_log,
            error_log=error_log,
            statsd_host=str(STATSD_HOST),
            enable_tracing=self._workload_config.tracing_enabled,
            config_entries=config_entries,
        )
        return config

    @property
    def _config_path(self) -> pathlib.Path:
        """Gets the path to the Gunicorn configuration file.

        Returns:
            The path to the web server configuration file.
        """
        return self._workload_config.base_dir / "gunicorn.conf.py"

    def update_config(
        self, environment: dict[str, str], is_webserver_running: bool, command: str
    ) -> None:
        """Update and apply the configuration file of the web server.

        Args:
            environment: Environment variables used to run the application.
            is_webserver_running: Indicates if the web server container is currently running.
            command: The WSGI application startup command.

        Raises:
            CharmConfigInvalidError: if the charm configuration is not valid.
        """
        self._prepare_log_dir()
        webserver_config_path = str(self._config_path)
        try:
            current_webserver_config = self._container.pull(webserver_config_path)
        except PathError:
            current_webserver_config = None
        self._container.push(
            webserver_config_path,
            self._config,
            user=self._workload_config.user,
            group=self._workload_config.group,
        )
        if current_webserver_config == self._config:
            return
        check_config_command = [x for x in shlex.split(command) if x not in ["[", "]"]]
        check_config_command.append("--check-config")
        exec_process = self._container.exec(
            check_config_command,
            environment=environment,
            user=self._workload_config.user,
            group=self._workload_config.group,
            working_dir=str(self._workload_config.app_dir),
        )
        try:
            exec_process.wait_output()
        except ExecError as exc:
            logger.error(
                "webserver configuration check failed, stdout: %s, stderr: %s",
                exc.stdout,
                exc.stderr,
            )
            raise CharmConfigInvalidError(
                "Webserver configuration check failed, "
                "please review your charm configuration or database relation"
            ) from exc
        if is_webserver_running:
            logger.info("gunicorn config changed, reloading")
            self._container.send_signal(self._reload_signal, self._workload_config.service_name)

    def _prepare_log_dir(self) -> None:
        """Prepare access and error log directory for the application."""
        container = self._container
        for log in self._workload_config.log_files:
            log_dir = str(log.parent.absolute())
            if not container.exists(log_dir):
                container.make_dir(
                    log_dir,
                    make_parents=True,
                    user=self._workload_config.user,
                    group=self._workload_config.group,
                )
