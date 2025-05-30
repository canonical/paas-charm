# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the base generic class to represent the application."""
import collections
import json
import logging
import pathlib
import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

import ops

from paas_charm.charm_state import CharmState
from paas_charm.database_migration import DatabaseMigration

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from charms.openfga_k8s.v1.openfga import OpenfgaProviderAppData
    from charms.smtp_integrator.v0.smtp import SmtpRelationData

    from paas_charm.databases import PaaSDatabaseRelationData
    from paas_charm.rabbitmq import PaaSRabbitMQRelationData
    from paas_charm.redis import PaaSRedisRelationData
    from paas_charm.s3 import PaaSS3RelationData
    from paas_charm.saml import PaaSSAMLRelationData
    from paas_charm.tracing import PaaSTracingRelationData

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
    container_name: str = "app"
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


def generate_openfga_env(relation_data: "OpenfgaProviderAppData | None" = None) -> dict[str, str]:
    """Generate environment variable from OpenFGA relation data.

    Args:
        relation_data: The charm OpenFGA integration relation data.

    Returns:
        OpenFGA environment mappings if OpenFGA requirer is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return {
        k: v
        for k, v in (
            ("FGA_STORE_ID", relation_data.store_id),
            ("FGA_TOKEN", relation_data.token),
            ("FGA_GRPC_API_URL", relation_data.grpc_api_url),
            ("FGA_HTTP_API_URL", relation_data.http_api_url),
        )
        if v is not None
    }


def generate_db_env(
    database_name: str, relation_data: "PaaSDatabaseRelationData | None" = None
) -> dict[str, str]:
    """Generate environment variable from Database relation data.

    Args:
        database_name: The name of the database, i.e. POSTGRESQL.
        relation_data: The charm database integration relation data.

    Returns:
        Default database environment mappings if DatabaseRelationData is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return _db_url_to_env_variables(database_name.upper(), relation_data.uris)


def generate_rabbitmq_env(
    relation_data: "PaaSRabbitMQRelationData | None" = None,
) -> dict[str, str]:
    """Generate environment variable from RabbitMQ requirer data.

    Args:
        relation_data: The charm RabbitMQ integration relation data.

    Returns:
        RabbitMQ environment mappings if RabbitMQ requirer is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    envvars = _url_env_vars(prefix="RABBITMQ", url=relation_data.amqp_uri)
    parsed_url = urllib.parse.urlparse(relation_data.amqp_uri)
    if len(parsed_url.path) > 1:
        envvars["RABBITMQ_VHOST"] = urllib.parse.unquote(parsed_url.path.split("/")[1])
    return envvars


def generate_redis_env(relation_data: "PaaSRedisRelationData | None" = None) -> dict[str, str]:
    """Generate environment variable from Redis relation data.

    Args:
        relation_data: The charm Redis integration relation data.

    Returns:
        Redis environment mappings if Redis relation data is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return _db_url_to_env_variables("REDIS", str(relation_data.url))


def generate_s3_env(relation_data: "PaaSS3RelationData | None" = None) -> dict[str, str]:
    """Generate environment variable from S3 relation data.

    Args:
        relation_data: The charm S3 integration relation data.

    Returns:
        Default S3 environment mappings if S3RelationData is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return {
        k: v
        for k, v in (
            ("S3_ACCESS_KEY", relation_data.access_key),
            ("S3_SECRET_KEY", relation_data.secret_key),
            ("S3_REGION", relation_data.region),
            ("S3_STORAGE_CLASS", relation_data.storage_class),
            ("S3_BUCKET", relation_data.bucket),
            ("S3_ENDPOINT", relation_data.endpoint),
            ("S3_PATH", relation_data.path),
            ("S3_API_VERSION", relation_data.s3_api_version),
            ("S3_URI_STYLE", relation_data.s3_uri_style),
            ("S3_ADDRESSING_STYLE", relation_data.addressing_style),
            (
                "S3_ATTRIBUTES",
                json.dumps(relation_data.attributes) if relation_data.attributes else None,
            ),
            (
                "S3_TLS_CA_CHAIN",
                json.dumps(relation_data.tls_ca_chain) if relation_data.attributes else None,
            ),
        )
        if v is not None
    }


def generate_saml_env(relation_data: "PaaSSAMLRelationData | None" = None) -> dict[str, str]:
    """Generate environment variable from SAML relation data.

    Args:
        relation_data: The charm SAML integration relation data.

    Returns:
        SAML environment mappings if SAML relation data is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return {
        k: v
        for (k, v) in (
            ("SAML_ENTITY_ID", relation_data.entity_id),
            (
                "SAML_METADATA_URL",
                str(relation_data.metadata_url) if relation_data.metadata_url else None,
            ),
            (
                "SAML_SINGLE_SIGN_ON_REDIRECT_URL",
                relation_data.single_sign_on_redirect_url,
            ),
            ("SAML_SIGNING_CERTIFICATE", relation_data.signing_certificate),
        )
        if v is not None
    }


def generate_smtp_env(relation_data: "SmtpRelationData | None" = None) -> dict[str, str]:
    """Generate environment variable from SMTP relation data.

    Args:
        relation_data: The charm SMTP integration relation data.

    Returns:
        SMTP environment mappings if SMTP relation data is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return {
        k: v
        for k, v in (
            ("SMTP_HOST", relation_data.host),
            ("SMTP_PORT", str(relation_data.port)),
            ("SMTP_USER", relation_data.user),
            ("SMTP_PASSWORD", relation_data.password),
            ("SMTP_AUTH_TYPE", relation_data.auth_type.value),
            ("SMTP_TRANSPORT_SECURITY", relation_data.transport_security.value),
            ("SMTP_DOMAIN", relation_data.domain),
            ("SMTP_SKIP_SSL_VERIFY", str(relation_data.skip_ssl_verify)),
        )
        if v is not None and v not in ("none")
    }


def generate_tempo_env(relation_data: "PaaSTracingRelationData | None" = None) -> dict[str, str]:
    """Generate environment variable from TempoRelationData.

    Args:
        relation_data: The charm Tempo integration relation data.

    Returns:
        Default Tempo tracing environment mappings if TempoRelationData is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return {
        k: v
        for k, v in (
            ("OTEL_SERVICE_NAME", relation_data.service_name),
            ("OTEL_EXPORTER_OTLP_ENDPOINT", str(relation_data.endpoint)),
        )
        if v is not None
    }


# too-many-instance-attributes is disabled because this class
# contains 1 more attributes than pylint allows
class App:  # pylint: disable=too-many-instance-attributes
    """Base class for the application manager.

    Attributes:
        generate_db_env: Maps database connection information to environment variables.
        generate_openfga_env: Maps OpenFGA connection information to environment variables.
        generate_rabbitmq_env: Maps RabbitMQ connection information to environment variables.
        generate_redis_env: Maps Redis connection information to environment variables.
        generate_s3_env: Maps S3 connection information to environment variables.
        generate_saml_env: Maps SAML connection information to environment variables.
        generate_smtp_env: Maps STMP connection information to environment variables.
        generate_tempo_env: Maps tempo tracing connection information to environment variables.
    """

    generate_db_env = staticmethod(generate_db_env)
    generate_openfga_env = staticmethod(generate_openfga_env)
    generate_rabbitmq_env = staticmethod(generate_rabbitmq_env)
    generate_redis_env = staticmethod(generate_redis_env)
    generate_s3_env = staticmethod(generate_s3_env)
    generate_saml_env = staticmethod(generate_saml_env)
    generate_smtp_env = staticmethod(generate_smtp_env)
    generate_tempo_env = staticmethod(generate_tempo_env)

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
            container: the application container.
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

    # 2024/04/25 - we're refactoring this method which will get rid of map_integrations_to_env
    # wrapper function. Ignore too-complex error from flake8 for now.
    def gen_environment(self) -> dict[str, str]:  # noqa: too-complex
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

        if self._charm_state.peer_fqdns is not None:
            env[f"{prefix}PEER_FQDNS"] = self._charm_state.peer_fqdns

        env.update(self._generate_integration_environments(prefix=self.integrations_prefix))
        return env

    def _generate_integration_environments(self, prefix: str = "") -> dict[str, str]:
        """Generate environment variables from integration data.

        Returns:
            Environment variable mappings for each relation data.
        """
        env: dict[str, str] = {}
        env.update(self.generate_openfga_env(relation_data=self._charm_state.integrations.openfga))
        env.update(
            self.generate_rabbitmq_env(relation_data=self._charm_state.integrations.rabbitmq)
        )
        env.update(self.generate_redis_env(relation_data=self._charm_state.integrations.redis))
        env.update(self.generate_s3_env(relation_data=self._charm_state.integrations.s3))
        for (
            database_name,
            db_relation_data,
        ) in self._charm_state.integrations.databases_relation_data.items():
            env.update(self.generate_db_env(database_name, db_relation_data))
        env.update(self.generate_saml_env(relation_data=self._charm_state.integrations.saml))
        env.update(self.generate_smtp_env(relation_data=self._charm_state.integrations.smtp))
        env.update(self.generate_tempo_env(relation_data=self._charm_state.integrations.tracing))
        return {prefix + k: v for (k, v) in env.items()}

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
