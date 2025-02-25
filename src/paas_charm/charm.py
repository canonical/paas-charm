# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""The base charm class for all application charms."""
import abc
import logging
import typing

import ops
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequiresEvent
from charms.redis_k8s.v0.redis import RedisRelationCharmEvents, RedisRequires
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from ops import RelationMeta
from ops.model import Container
from pydantic import BaseModel, ValidationError

from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState, IntegrationRequirers
from paas_charm.charm_utils import block_if_invalid_config
from paas_charm.database_migration import DatabaseMigration, DatabaseMigrationStatus
from paas_charm.databases import make_database_requirers
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.observability import Observability
from paas_charm.rabbitmq import RabbitMQRequires
from paas_charm.secret_storage import KeySecretStorage
from paas_charm.utils import build_validation_error_message, config_get_with_secret

logger = logging.getLogger(__name__)

# Until charmcraft fetch-libs is implemented, the charm will not fail
# if new optional libs are not fetched, as it will not be backwards compatible.
try:
    # pylint: disable=ungrouped-imports
    from charms.data_platform_libs.v0.s3 import S3Requirer
except ImportError:
    logger.warning(
        "Missing charm library, please run `charmcraft fetch-lib charms.data_platform_libs.v0.s3`"
    )

try:
    # pylint: disable=ungrouped-imports
    from charms.saml_integrator.v0.saml import SamlRequires
except ImportError:
    logger.warning(
        "Missing charm library, please run `charmcraft fetch-lib charms.saml_integrator.v0.saml`"
    )

try:
    # pylint: disable=ungrouped-imports
    from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer
except ImportError:
    logger.warning(
        "Missing charm library, please run "
        "`charmcraft fetch-lib charms.tempo_coordinator_k8s.v0.tracing`"
    )

try:
    # pylint: disable=ungrouped-imports
    from charms.smtp_integrator.v0.smtp import SmtpRequires
except ImportError:
    logger.warning(
        "Missing charm library, please run "
        "`charmcraft fetch-lib charms.smtp_integrator.v0.smtp`"
    )


class PaasCharm(abc.ABC, ops.CharmBase):  # pylint: disable=too-many-instance-attributes
    """PaasCharm base charm service mixin.

    Attrs:
        on: charm events replaced by Redis ones for the Redis charm library.
        framework_config_class: base class for the framework config.
    """

    framework_config_class: type[BaseModel]

    @abc.abstractmethod
    def get_cos_dir(self) -> str:
        """Return the directory with COS related files."""

    @property
    @abc.abstractmethod
    def _workload_config(self) -> WorkloadConfig:
        """Return an WorkloadConfig instance."""

    @abc.abstractmethod
    def _create_app(self) -> App:
        """Create an App instance."""

    on = RedisRelationCharmEvents()

    def __init__(self, framework: ops.Framework, framework_name: str) -> None:
        """Initialize the instance.

        Args:
            framework: operator framework.
            framework_name: framework name.
        """
        super().__init__(framework)
        self._framework_name = framework_name

        self._secret_storage = KeySecretStorage(charm=self, key=f"{framework_name}_secret_key")
        self._database_requirers = make_database_requirers(self, self.app.name)

        requires: dict[str, RelationMeta] = self.framework.meta.requires
        self._redis = self._init_redis(requires)
        self._s3 = self._init_s3(requires)
        self._saml = self._init_saml(requires)
        self._rabbitmq = self._init_rabbitmq(requires)
        self._tracing = self._init_tracing(requires)
        self._smtp = self._init_smtp(requires)

        self._database_migration = DatabaseMigration(
            container=self.unit.get_container(self._workload_config.container_name),
            state_dir=self._workload_config.state_dir,
        )

        self._ingress = IngressPerAppRequirer(
            self,
            port=self._workload_config.port,
            strip_prefix=True,
        )

        self._observability = Observability(
            charm=self,
            log_files=self._workload_config.log_files,
            container_name=self._workload_config.container_name,
            cos_dir=self.get_cos_dir(),
            metrics_target=self._workload_config.metrics_target,
            metrics_path=self._workload_config.metrics_path,
        )

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.rotate_secret_key_action, self._on_rotate_secret_key_action)
        self.framework.observe(
            self.on.secret_storage_relation_changed,
            self._on_secret_storage_relation_changed,
        )
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(self.on.secret_changed, self._on_secret_changed)
        for database, database_requirer in self._database_requirers.items():
            self.framework.observe(
                database_requirer.on.database_created,
                getattr(self, f"_on_{database}_database_database_created"),
            )
            self.framework.observe(
                database_requirer.on.endpoints_changed,
                getattr(self, f"_on_{database}_database_endpoints_changed"),
            )
            self.framework.observe(
                self.on[database_requirer.relation_name].relation_broken,
                getattr(self, f"_on_{database}_database_relation_broken"),
            )
        self.framework.observe(self._ingress.on.ready, self._on_ingress_ready)
        self.framework.observe(self._ingress.on.revoked, self._on_ingress_revoked)
        self.framework.observe(
            self.on[self._workload_config.container_name].pebble_ready, self._on_pebble_ready
        )

    def _init_redis(self, requires: dict[str, RelationMeta]) -> "RedisRequires | None":
        """Initialize the Redis relation if its required.

        Args:
            requires: relation requires dictionary from metadata

        Returns:
            Returns the Redis relation or None
        """
        _redis = None
        if "redis" in requires and requires["redis"].interface_name == "redis":
            try:
                _redis = RedisRequires(charm=self, relation_name="redis")
                self.framework.observe(
                    self.on.redis_relation_updated, self._on_redis_relation_updated
                )
            except NameError:
                logger.exception(
                    "Missing charm library,                               "
                    "please run `charmcraft fetch-lib charms.redis_k8s.v0.redis`"
                )

        return _redis

    def _init_s3(self, requires: dict[str, RelationMeta]) -> "S3Requirer | None":
        """Initialize the S3 relation if its required.

        Args:
            requires: relation requires dictionary from metadata

        Returns:
            Returns the S3 relation or None
        """
        _s3 = None
        if "s3" in requires and requires["s3"].interface_name == "s3":
            try:
                _s3 = S3Requirer(charm=self, relation_name="s3", bucket_name=self.app.name)
                self.framework.observe(_s3.on.credentials_changed, self._on_s3_credential_changed)
                self.framework.observe(_s3.on.credentials_gone, self._on_s3_credential_gone)
            except NameError:
                logger.exception(
                    "Missing charm library, "
                    "please run `charmcraft fetch-lib charms.data_platform_libs.v0.s3`"
                )
        return _s3

    def _init_saml(self, requires: dict[str, RelationMeta]) -> "SamlRequires | None":
        """Initialize the SAML relation if its required.

        Args:
            requires: relation requires dictionary from metadata

        Returns:
            Returns the SAML relation or None
        """
        _saml = None
        if "saml" in requires and requires["saml"].interface_name == "saml":
            try:
                _saml = SamlRequires(self)
                self.framework.observe(_saml.on.saml_data_available, self._on_saml_data_available)
            except NameError:
                logger.exception(
                    "Missing charm library, "
                    "please run `charmcraft fetch-lib charms.saml_integrator.v0.saml`"
                )
        return _saml

    def _init_rabbitmq(self, requires: dict[str, RelationMeta]) -> "RabbitMQRequires | None":
        """Initialize the RabbitMQ relation if its required.

        Args:
            requires: relation requires dictionary from metadata

        Returns:
            Returns the RabbitMQ relation or None
        """
        _rabbitmq = None
        if "rabbitmq" in requires and requires["rabbitmq"].interface_name == "rabbitmq":
            _rabbitmq = RabbitMQRequires(
                self,
                "rabbitmq",
                username=self.app.name,
                vhost="/",
            )
            self.framework.observe(_rabbitmq.on.connected, self._on_rabbitmq_connected)
            self.framework.observe(_rabbitmq.on.ready, self._on_rabbitmq_ready)
            self.framework.observe(_rabbitmq.on.departed, self._on_rabbitmq_departed)

        return _rabbitmq

    def _init_tracing(self, requires: dict[str, RelationMeta]) -> "TracingEndpointRequirer | None":
        """Initialize the Tracing relation if its required.

        Args:
            requires: relation requires dictionary from metadata

        Returns:
            Returns the Tracing relation or None
        """
        _tracing = None
        if "tracing" in requires and requires["tracing"].interface_name == "tracing":
            try:
                _tracing = TracingEndpointRequirer(
                    self, relation_name="tracing", protocols=["otlp_http"]
                )
                self.framework.observe(
                    _tracing.on.endpoint_changed, self._on_tracing_relation_changed
                )
                self.framework.observe(
                    _tracing.on.endpoint_removed, self._on_tracing_relation_broken
                )
            except NameError:
                logger.exception(
                    "Missing charm library, please run "
                    "`charmcraft fetch-lib charms.tempo_coordinator_k8s.v0.tracing`"
                )
        return _tracing

    def _init_smtp(self, requires: dict[str, RelationMeta]) -> "SmtpRequires | None":
        """Initialize the Smtp relation if its required.

        Args:
            requires: relation requires dictionary from metadata

        Returns:
            Returns the Smtp relation or None
        """
        _smtp = None
        if "smtp" in requires and requires["smtp"].interface_name == "smtp":
            try:
                _smtp = SmtpRequires(self)
                self.framework.observe(_smtp.on.smtp_data_available, self._on_smtp_data_available)
            except NameError:
                logger.exception(
                    "Missing charm library, please run "
                    "`charmcraft fetch-lib charms.smtp_integrator.v0.smtp`"
                )
        return _smtp

    def get_framework_config(self) -> BaseModel:
        """Return the framework related configurations.

        Raises:
            CharmConfigInvalidError: if charm config is not valid.

        Returns:
             Framework related configurations.
        """
        # Will raise an AttributeError if it the attribute framework_config_class does not exist.
        framework_config_class = self.framework_config_class
        charm_config = {k: config_get_with_secret(self, k) for k in self.config.keys()}
        config = typing.cast(
            dict,
            {
                k: v.get_content(refresh=True) if isinstance(v, ops.Secret) else v
                for k, v in charm_config.items()
            },
        )

        try:
            return framework_config_class.model_validate(config)
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc)
            logger.error(error_messages.long)
            raise CharmConfigInvalidError(error_messages.short) from exc

    @property
    def _container(self) -> Container:
        """Return the workload container."""
        return self.unit.get_container(self._workload_config.container_name)

    @block_if_invalid_config
    def _on_config_changed(self, _: ops.EventBase) -> None:
        """Configure the application pebble service layer."""
        self.restart()

    @block_if_invalid_config
    def _on_secret_changed(self, _: ops.EventBase) -> None:
        """Configure the application Pebble service layer."""
        self.restart()

    @block_if_invalid_config
    def _on_rotate_secret_key_action(self, event: ops.ActionEvent) -> None:
        """Handle the rotate-secret-key action.

        Args:
            event: the action event that trigger this callback.
        """
        if not self.unit.is_leader():
            event.fail("only leader unit can rotate secret key")
            return
        if not self._secret_storage.is_initialized:
            event.fail("charm is still initializing")
            return
        self._secret_storage.reset_secret_key()
        event.set_results({"status": "success"})
        self.restart()

    @block_if_invalid_config
    def _on_secret_storage_relation_changed(self, _: ops.RelationEvent) -> None:
        """Handle the secret-storage-relation-changed event."""
        self.restart()

    def update_app_and_unit_status(self, status: ops.StatusBase) -> None:
        """Update the application and unit status.

        Args:
            status: the desired application and unit status.
        """
        self.unit.status = status
        if self.unit.is_leader():
            self.app.status = status

    def is_ready(self) -> bool:
        """Check if the charm is ready to start the workload application.

        Returns:
            True if the charm is ready to start the workload application.
        """
        charm_state = self._create_charm_state()

        if not self._container.can_connect():
            logger.info(
                "pebble client in the %s container is not ready", self._workload_config.framework
            )
            self.update_app_and_unit_status(ops.WaitingStatus("Waiting for pebble ready"))
            return False
        if not charm_state.is_secret_storage_ready:
            logger.info("secret storage is not initialized")
            self.update_app_and_unit_status(ops.WaitingStatus("Waiting for peer integration"))
            return False

        missing_integrations = list(self._missing_required_integrations(charm_state))
        if missing_integrations:
            self._create_app().stop_all_services()
            self._database_migration.set_status_to_pending()
            message = f"missing integrations: {', '.join(missing_integrations)}"
            logger.info(message)
            self.update_app_and_unit_status(ops.BlockedStatus(message))
            return False

        return True

    def _missing_required_database_integrations(
        self, requires: dict[str, RelationMeta], charm_state: CharmState
    ) -> typing.Generator:
        """Return required database integrations.

        Args:
            requires: relation requires dictionary from metadata
            charm_state: current charm state
        """
        for name in self._database_requirers.keys():
            if (
                name not in charm_state.integrations.databases_uris
                or charm_state.integrations.databases_uris[name] is None
            ):
                if not requires[name].optional:
                    yield name

        if self._rabbitmq and not charm_state.integrations.rabbitmq_uri:
            if not requires["rabbitmq"].optional:
                yield "rabbitmq"

    def _missing_required_storage_integrations(
        self, requires: dict[str, RelationMeta], charm_state: CharmState
    ) -> typing.Generator:
        """Return required storage integrations.

        Args:
            requires: relation requires dictionary from metadata
            charm_state: current charm state
        """
        if self._redis and not charm_state.integrations.redis_uri:
            if not requires["redis"].optional:
                yield "redis"

        if self._s3 and not charm_state.integrations.s3_parameters:
            if not requires["s3"].optional:
                yield "s3"

    def _missing_required_other_integrations(
        self, requires: dict[str, RelationMeta], charm_state: CharmState
    ) -> typing.Generator:
        """Return required various integrations.

        Args:
            requires: relation requires dictionary from metadata
            charm_state: current charm state
        """
        if self._saml and not charm_state.integrations.saml_parameters:
            if not requires["saml"].optional:
                yield "saml"

        if self._tracing and not charm_state.integrations.tempo_parameters:
            if not requires["tracing"].optional:
                yield "tracing"

        if self._smtp and not charm_state.integrations.smtp_parameters:
            if not requires["smtp"].optional:
                yield "smtp"

    def _missing_required_integrations(
        self, charm_state: CharmState
    ) -> typing.Generator:  # noqa: C901
        """Get list of missing integrations that are required.

        Args:
            charm_state: the charm state
        """
        requires = self.framework.meta.requires
        yield from self._missing_required_database_integrations(requires, charm_state)
        yield from self._missing_required_storage_integrations(requires, charm_state)
        yield from self._missing_required_other_integrations(requires, charm_state)

    def restart(self, rerun_migrations: bool = False) -> None:
        """Restart or start the service if not started with the latest configuration.

        Args:
            rerun_migrations: whether it is necessary to run the migrations again.
        """
        if rerun_migrations:
            self._database_migration.set_status_to_pending()

        if not self.is_ready():
            return
        try:
            self.update_app_and_unit_status(ops.MaintenanceStatus("Preparing service for restart"))
            self._create_app().restart()
        except CharmConfigInvalidError as exc:
            self.update_app_and_unit_status(ops.BlockedStatus(exc.msg))
            return
        self.unit.open_port("tcp", self._workload_config.port)
        self.update_app_and_unit_status(ops.ActiveStatus())

    def _gen_environment(self) -> dict[str, str]:
        """Generate the environment dictionary used for the App.

        This method is useful to generate the environment variables to
        run actions against the workload container for subclasses.

        Returns:
            A dictionary representing the application environment variables.
        """
        return self._create_app().gen_environment()

    def _create_charm_state(self) -> CharmState:
        """Create charm state.

        This method may raise CharmConfigInvalidError.

        Returns:
            New CharmState
        """
        charm_config = {k: config_get_with_secret(self, k) for k in self.config.keys()}
        config = typing.cast(
            dict,
            {
                k: v.get_content(refresh=True) if isinstance(v, ops.Secret) else v
                for k, v in charm_config.items()
            },
        )
        return CharmState.from_charm(
            config=config,
            framework=self._framework_name,
            framework_config=self.get_framework_config(),
            secret_storage=self._secret_storage,
            integration_requirers=IntegrationRequirers(
                databases=self._database_requirers,
                redis=self._redis,
                rabbitmq=self._rabbitmq,
                s3=self._s3,
                saml=self._saml,
                tracing=self._tracing,
                smtp=self._smtp,
            ),
            app_name=self.app.name,
            base_url=self._base_url,
        )

    @property
    def _base_url(self) -> str:
        """Return the base_url for the service.

        This URL will be the ingress URL if there is one, otherwise it will
        point to the K8S service.
        """
        if self._ingress.url:
            return self._ingress.url
        return f"http://{self.app.name}.{self.model.name}:{self._workload_config.port}"

    @block_if_invalid_config
    def _on_update_status(self, _: ops.HookEvent) -> None:
        """Handle the update-status event."""
        if self._database_migration.get_status() == DatabaseMigrationStatus.FAILED:
            self.restart()

    @block_if_invalid_config
    def _on_mysql_database_database_created(self, _: DatabaseRequiresEvent) -> None:
        """Handle mysql's database-created event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_mysql_database_endpoints_changed(self, _: DatabaseRequiresEvent) -> None:
        """Handle mysql's endpoints-changed event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_mysql_database_relation_broken(self, _: ops.RelationBrokenEvent) -> None:
        """Handle mysql's relation-broken event."""
        self.restart()

    @block_if_invalid_config
    def _on_postgresql_database_database_created(self, _: DatabaseRequiresEvent) -> None:
        """Handle postgresql's database-created event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_postgresql_database_endpoints_changed(self, _: DatabaseRequiresEvent) -> None:
        """Handle mysql's endpoints-changed event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_postgresql_database_relation_broken(self, _: ops.RelationBrokenEvent) -> None:
        """Handle postgresql's relation-broken event."""
        self.restart()

    @block_if_invalid_config
    def _on_mongodb_database_database_created(self, _: DatabaseRequiresEvent) -> None:
        """Handle mongodb's database-created event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_mongodb_database_endpoints_changed(self, _: DatabaseRequiresEvent) -> None:
        """Handle mysql's endpoints-changed event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_mongodb_database_relation_broken(self, _: ops.RelationBrokenEvent) -> None:
        """Handle postgresql's relation-broken event."""
        self.restart()

    @block_if_invalid_config
    def _on_redis_relation_updated(self, _: DatabaseRequiresEvent) -> None:
        """Handle redis's database-created event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_s3_credential_changed(self, _: ops.HookEvent) -> None:
        """Handle s3 credentials-changed event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_s3_credential_gone(self, _: ops.HookEvent) -> None:
        """Handle s3 credentials-gone event."""
        self.restart()

    @block_if_invalid_config
    def _on_saml_data_available(self, _: ops.HookEvent) -> None:
        """Handle saml data available event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_ingress_revoked(self, _: ops.HookEvent) -> None:
        """Handle event for ingress revoked."""
        self.restart()

    @block_if_invalid_config
    def _on_ingress_ready(self, _: ops.HookEvent) -> None:
        """Handle event for ingress ready."""
        self.restart()

    @block_if_invalid_config
    def _on_pebble_ready(self, _: ops.PebbleReadyEvent) -> None:
        """Handle the pebble-ready event."""
        self.restart()

    @block_if_invalid_config
    def _on_rabbitmq_connected(self, _: ops.HookEvent) -> None:
        """Handle rabbitmq connected event."""
        self.restart()

    @block_if_invalid_config
    def _on_rabbitmq_ready(self, _: ops.HookEvent) -> None:
        """Handle rabbitmq ready event."""
        self.restart(rerun_migrations=True)

    @block_if_invalid_config
    def _on_rabbitmq_departed(self, _: ops.HookEvent) -> None:
        """Handle rabbitmq departed event."""
        self.restart()

    @block_if_invalid_config
    def _on_tracing_relation_changed(self, _: ops.HookEvent) -> None:
        """Handle tracing relation changed event."""
        self.restart()

    @block_if_invalid_config
    def _on_tracing_relation_broken(self, _: ops.HookEvent) -> None:
        """Handle tracing relation broken event."""
        self.restart()

    @block_if_invalid_config
    def _on_smtp_data_available(self, _: ops.HookEvent) -> None:
        """Handle smtp data available event."""
        self.restart()
