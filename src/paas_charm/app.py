# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the base generic class to represent the application."""
import collections
import json
import logging
import pathlib
import urllib.parse
from dataclasses import dataclass
from typing import List

import ops

from paas_charm.charm_state import CharmState, IntegrationsState
from paas_charm.database_migration import DatabaseMigration

logger = logging.getLogger(__name__)

WORKER_SUFFIX = "-worker"
SCHEDULER_SUFFIX = "-scheduler"


@dataclass(kw_only=True)
class WorkloadConfig:  # pylint: disable=too-many-instance-attributes
    """Main Configuration for the workload of an App.

    This class contains attributes that are configuration for the app/workload.

    Attrs:
        framework: the framework name.
        container_name: the container name.
        port: the port number to use for the server.
        user: the UNIX user name for running the service.
        group: the UNIX group name for running the service.
        base_dir: the project base directory in the application container.
        app_dir: the application directory in the application container.
        state_dir: the directory in the application container to store states information.
        service_name: the WSGI application pebble service name.
        log_files: list of files to monitor.
        metrics_target: target to scrape for metrics.
        metrics_path: path to scrape for metrics.
        unit_name: Name of the unit. Needed to know if schedulers should run here.
        tracing_enabled: True if tracing should be enabled.
    """

    framework: str
    container_name: str
    port: int
    user: str = "_daemon_"
    group: str = "_daemon_"
    base_dir: pathlib.Path
    app_dir: pathlib.Path
    state_dir: pathlib.Path
    service_name: str
    log_files: List[pathlib.Path]
    metrics_target: str | None = None
    metrics_path: str | None = "/metrics"
    unit_name: str
    tracing_enabled: bool = False

    def should_run_scheduler(self) -> bool:
        """Return if the unit should run scheduler processes.

        Return:
            True if the unit should run scheduler processes, False otherwise.
        """
        unit_id = self.unit_name.split("/")[1]
        return unit_id == "0"


# too-many-instance-attributes is disabled because this class
# contains 1 more attributes than pylint allows
class App:  # pylint: disable=too-many-instance-attributes
    """Base class for the application manager."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        container: ops.Container,
        charm_state: CharmState,
        workload_config: WorkloadConfig,
        database_migration: DatabaseMigration,
        framework_config_prefix: str = "APP_",
        configuration_prefix: str = "APP_",
        integrations_prefix: str = "",
    ):
        """Construct the App instance.

        Args:
            container: phe application container.
            charm_state: the state of the charm.
            workload_config: the state of the workload that the App belongs to.
            database_migration: the database migration manager object.
            framework_config_prefix: prefix for environment variables related to framework config.
            configuration_prefix: prefix for environment variables related to configuration.
            integrations_prefix: prefix for environment variables related to integrations.
        """
        self.__alternate_service_command: str | None = None
        self._container = container
        self._charm_state = charm_state
        self._workload_config = workload_config
        self._database_migration = database_migration
        self.framework_config_prefix = framework_config_prefix
        self.configuration_prefix = configuration_prefix
        self.integrations_prefix = integrations_prefix

    def stop_all_services(self) -> None:
        """Stop all the services in the workload.

        Services will restarted again when the restart method is invoked.
        """
        services = self._container.get_services()
        service_names = list(services.keys())
        if service_names:
            self._container.stop(*service_names)

    def restart(self) -> None:
        """Restart or start the service if not started with the latest configuration."""
        self._container.add_layer("charm", self._app_layer(), combine=True)
        self._prepare_service_for_restart()
        self._run_migrations()
        self._container.replan()

    def gen_environment(self) -> dict[str, str]:
        """Generate a environment dictionary from the charm configurations.

        The environment generation follows these rules:
             1. User-defined configuration cannot overwrite built-in framework configurations,
                even if the built-in framework application configuration value is None (undefined).
             2. Boolean and integer-typed configuration values will be JSON encoded before
                being passed to application.
             3. String-typed configuration values will be passed to the application as environment
                variables directly.
             4. Different prefixes can be set to the environment variable names depending on the
                framework.

        Returns:
            A dictionary representing the application environment variables.
        """
        prefix = self.configuration_prefix
        env = {}
        for app_config_key, app_config_value in self._charm_state.user_defined_config.items():
            if isinstance(app_config_value, collections.abc.Mapping):
                for k, v in app_config_value.items():
                    env[f"{prefix}{app_config_key.upper()}_{k.replace('-', '_').upper()}"] = (
                        encode_env(v)
                    )
            else:
                env[f"{prefix}{app_config_key.upper()}"] = encode_env(app_config_value)

        framework_config = self._charm_state.framework_config
        framework_config_prefix = self.framework_config_prefix
        env.update(
            {
                f"{framework_config_prefix}{k.upper()}": encode_env(v)
                for k, v in framework_config.items()
            }
        )

        if self._charm_state.base_url:
            env[f"{prefix}BASE_URL"] = self._charm_state.base_url
        secret_key_env = f"{prefix}SECRET_KEY"
        if secret_key_env not in env:
            env[secret_key_env] = self._charm_state.secret_key
        for proxy_variable in ("http_proxy", "https_proxy", "no_proxy"):
            proxy_value = getattr(self._charm_state.proxy, proxy_variable)
            if proxy_value:
                env[proxy_variable] = str(proxy_value)
                env[proxy_variable.upper()] = str(proxy_value)

        if self._charm_state.integrations:
            env.update(
                map_integrations_to_env(
                    self._charm_state.integrations, prefix=self.integrations_prefix
                )
            )
        return env

    @property
    def _alternate_service_command(self) -> str | None:
        """Specific framework operations before starting the service."""
        return self.__alternate_service_command

    @_alternate_service_command.setter
    def _alternate_service_command(self, value: str | None) -> None:
        """Specific framework operations before starting the service."""
        self.__alternate_service_command = value

    def _prepare_service_for_restart(self) -> None:
        """Specific framework operations before restarting the service."""

    def _run_migrations(self) -> None:
        """Run migrations."""
        migration_command = None
        app_dir = self._workload_config.app_dir
        if self._container.exists(app_dir / "migrate"):
            migration_command = [str((app_dir / "migrate").absolute())]
        if self._container.exists(app_dir / "migrate.sh"):
            migration_command = ["bash", "-eo", "pipefail", "migrate.sh"]
        if self._container.exists(app_dir / "migrate.py"):
            migration_command = ["python3", "migrate.py"]
        if self._container.exists(app_dir / "manage.py"):
            # Django migrate command
            migration_command = ["python3", "manage.py", "migrate"]
        if migration_command:
            self._database_migration.run(
                command=migration_command,
                environment=self.gen_environment(),
                working_dir=app_dir,
                user=self._workload_config.user,
                group=self._workload_config.group,
            )

    def _app_layer(self) -> ops.pebble.LayerDict:
        """Generate the pebble layer definition for the application.

        Returns:
            The pebble layer definition for the application.
        """
        original_services_file = self._workload_config.state_dir / "original-services.json"
        if self._container.exists(original_services_file):
            services = json.loads(self._container.pull(original_services_file).read())
        else:
            plan = self._container.get_plan()
            services = {k: v.to_dict() for k, v in plan.services.items()}
            self._container.push(original_services_file, json.dumps(services), make_dirs=True)

        services[self._workload_config.service_name]["override"] = "replace"
        services[self._workload_config.service_name]["environment"] = self.gen_environment()
        if self._alternate_service_command:
            services[self._workload_config.service_name][
                "command"
            ] = self._alternate_service_command

        for service_name, service in services.items():
            normalised_service_name = service_name.lower()
            # Add environment variables to all worker processes.
            if normalised_service_name.endswith(WORKER_SUFFIX):
                service["environment"] = self.gen_environment()
            # For scheduler processes, add environment variables if
            # the scheduler should run in the unit, disable it otherwise.
            if normalised_service_name.endswith(SCHEDULER_SUFFIX):
                if self._workload_config.should_run_scheduler():
                    service["environment"] = self.gen_environment()
                else:
                    service["startup"] = "disabled"

        return ops.pebble.LayerDict(services=services)


def encode_env(value: str | int | float | bool | list | dict) -> str:
    """Encode the environment variable values.

    Args:
        value: the input environment variable value.

    Return:
        The original string if the input is a string, or JSON encoded value.
    """
    return value if isinstance(value, str) else json.dumps(value)


def map_integrations_to_env(integrations: IntegrationsState, prefix: str = "") -> dict[str, str]:
    """Generate environment variables for the IntegrationState.

    Args:
       integrations: the IntegrationsState information.
       prefix: prefix to append to the env variables.

    Returns:
       A dictionary representing the environment variables for the IntegrationState.
    """
    env = {}
    if integrations.redis_uri:
        redis_envvars = _db_url_to_env_variables("REDIS", integrations.redis_uri)
        env.update(redis_envvars)
    for interface_name, uri in integrations.databases_uris.items():
        interface_envvars = _db_url_to_env_variables(interface_name.upper(), uri)
        env.update(interface_envvars)
    if integrations.tempo_parameters:
        if service_name := integrations.tempo_parameters.service_name:
            env.update({"OTEL_SERVICE_NAME": service_name})
        if endpoint := integrations.tempo_parameters.endpoint:
            env.update({"OTEL_EXPORTER_OTLP_ENDPOINT": endpoint})

    if integrations.s3_parameters:
        s3 = integrations.s3_parameters
        env.update(
            (k, v)
            for k, v in (
                ("S3_ACCESS_KEY", s3.access_key),
                ("S3_SECRET_KEY", s3.secret_key),
                ("S3_REGION", s3.region),
                ("S3_STORAGE_CLASS", s3.storage_class),
                ("S3_BUCKET", s3.bucket),
                ("S3_ENDPOINT", s3.endpoint),
                ("S3_PATH", s3.path),
                ("S3_API_VERSION", s3.s3_api_version),
                ("S3_URI_STYLE", s3.s3_uri_style),
                ("S3_ADDRESSING_STYLE", s3.addressing_style),
                ("S3_ATTRIBUTES", json.dumps(s3.attributes) if s3.attributes else None),
                ("S3_TLS_CA_CHAIN", json.dumps(s3.tls_ca_chain) if s3.attributes else None),
            )
            if v is not None
        )

    if integrations.saml_parameters:
        saml = integrations.saml_parameters
        env.update(
            (k, v)
            for k, v in (
                ("SAML_ENTITY_ID", saml.entity_id),
                ("SAML_METADATA_URL", saml.metadata_url),
                ("SAML_SINGLE_SIGN_ON_REDIRECT_URL", saml.single_sign_on_redirect_url),
                ("SAML_SIGNING_CERTIFICATE", saml.signing_certificate),
            )
            if v is not None
        )

    if integrations.rabbitmq_uri:
        rabbitmq_envvars = _rabbitmq_uri_to_env_variables("RABBITMQ", integrations.rabbitmq_uri)
        env.update(rabbitmq_envvars)

    if integrations.smtp_parameters:
        smtp = integrations.smtp_parameters
        env.update(
            (k, v)
            for k, v in (
                ("SMTP_HOST", smtp.host),
                ("SMTP_PORT", str(smtp.port)),
                ("SMTP_USER", smtp.user),
                ("SMTP_PASSWORD", smtp.password),
                ("SMTP_AUTH_TYPE", smtp.auth_type),
                ("SMTP_TRANSPORT_SECURITY", smtp.transport_security),
                ("SMTP_DOMAIN", smtp.domain),
                ("SMTP_SKIP_SSL_VERIFY", smtp.skip_ssl_verify),
            )
            if v is not None
        )

    return {prefix + k: v for k, v in env.items()}


def _db_url_to_env_variables(prefix: str, url: str) -> dict[str, str]:
    """Convert a database url to environment variables.

    Args:
      prefix: prefix for the environment variables
      url: url of the database

    Return:
      All environment variables, that is, the connection string,
      all components as returned from urllib.parse and the
      database name extracted from the path
    """
    prefix = prefix + "_DB"
    envvars = _url_env_vars(prefix, url)
    parsed_url = urllib.parse.urlparse(url)

    # database name is usually parsed this way.
    db_name = parsed_url.path.removeprefix("/") if parsed_url.path else None
    if db_name is not None:
        envvars[f"{prefix}_NAME"] = db_name
    return envvars


def _rabbitmq_uri_to_env_variables(prefix: str, url: str) -> dict[str, str]:
    """Convert a rabbitmq uri to environment variables.

    Args:
      prefix: prefix for the environment variables
      url: url of rabbitmq

    Return:
      All environment variables, that is, the connection string,
      all components as returned from urllib.parse and the
      rabbitmq vhost extracted from the path
    """
    envvars = _url_env_vars(prefix, url)
    parsed_url = urllib.parse.urlparse(url)
    if len(parsed_url.path) > 1:
        envvars[f"{prefix}_VHOST"] = urllib.parse.unquote(parsed_url.path.split("/")[1])
    return envvars


def _url_env_vars(prefix: str, url: str) -> dict[str, str]:
    """Convert a url to environment variables using parts from urllib.parse.urlparse.

    Args:
      prefix: prefix for the environment variables
      url: url of the database

    Return:
      All environment variables, that is, the connection string and
      all components as returned from urllib.parse
    """
    if not url:
        return {}

    envvars: dict[str, str | None] = {}
    envvars[f"{prefix}_CONNECT_STRING"] = url

    parsed_url = urllib.parse.urlparse(url)

    # All components of urlparse, using the same convention for default values.
    # See: https://docs.python.org/3/library/urllib.parse.html#url-parsing
    envvars[f"{prefix}_SCHEME"] = parsed_url.scheme
    envvars[f"{prefix}_NETLOC"] = parsed_url.netloc
    envvars[f"{prefix}_PATH"] = parsed_url.path
    envvars[f"{prefix}_PARAMS"] = parsed_url.params
    envvars[f"{prefix}_QUERY"] = parsed_url.query
    envvars[f"{prefix}_FRAGMENT"] = parsed_url.fragment
    envvars[f"{prefix}_USERNAME"] = parsed_url.username
    envvars[f"{prefix}_PASSWORD"] = parsed_url.password
    envvars[f"{prefix}_HOSTNAME"] = parsed_url.hostname
    envvars[f"{prefix}_PORT"] = str(parsed_url.port) if parsed_url.port is not None else None

    return {k: v for k, v in envvars.items() if v is not None}
