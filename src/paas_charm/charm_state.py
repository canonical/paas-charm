# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""This module defines the CharmState class which represents the state of the charm."""
import logging
import os
import pathlib
import typing
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError, create_model

from paas_charm.exceptions import CharmConfigInvalidError, InvalidRelationDataError
from paas_charm.secret_storage import KeySecretStorage
from paas_charm.utils import build_validation_error_message, config_metadata

# This is just for type checking, no need to cover this code.
if typing.TYPE_CHECKING:  # pragma: nocover
    from charms.openfga_k8s.v1.openfga import OpenfgaProviderAppData, OpenFGARequires
    from charms.smtp_integrator.v0.smtp import SmtpRelationData, SmtpRequires

    from paas_charm.databases import PaaSDatabaseRelationData, PaaSDatabaseRequires
    from paas_charm.rabbitmq import PaaSRabbitMQRelationData, RabbitMQRequires
    from paas_charm.redis import PaaSRedisRelationData, PaaSRedisRequires
    from paas_charm.s3 import PaaSS3RelationData, PaaSS3Requirer
    from paas_charm.saml import PaaSSAMLRelationData, PaaSSAMLRequirer
    from paas_charm.tracing import PaaSTracingEndpointRequirer, PaaSTracingRelationData

logger = logging.getLogger(__name__)


# too-many-instance-attributes is okay since we use a factory function to construct the CharmState
class CharmState:  # pylint: disable=too-many-instance-attributes
    """Represents the state of the charm.

    Attrs:
        framework_config: the value of the framework specific charm configuration.
        user_defined_config: user-defined configurations for the application.
        secret_key: the charm managed application secret key.
        is_secret_storage_ready: whether the secret storage system is ready.
        proxy: proxy information.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        framework: str,
        is_secret_storage_ready: bool,
        user_defined_config: dict[str, int | str | bool | dict[str, str]] | None = None,
        framework_config: dict[str, int | str] | None = None,
        secret_key: str | None = None,
        peer_fqdns: str | None = None,
        integrations: "IntegrationsState | None" = None,
        base_url: str | None = None,
    ):
        """Initialize a new instance of the CharmState class.

        Args:
            framework: the framework name.
            is_secret_storage_ready: whether the secret storage system is ready.
            user_defined_config: User-defined configuration values for the application.
            framework_config: The value of the framework application specific charm configuration.
            secret_key: The secret storage manager associated with the charm.
            peer_fqdns: The FQDN of units in the peer relation.
            integrations: Information about the integrations.
            base_url: Base URL for the service.
        """
        self.framework = framework
        self._framework_config = framework_config if framework_config is not None else {}
        self._user_defined_config = user_defined_config if user_defined_config is not None else {}
        self._is_secret_storage_ready = is_secret_storage_ready
        self._secret_key = secret_key
        self.peer_fqdns = peer_fqdns
        self.integrations = integrations or IntegrationsState()
        self.base_url = base_url

    @classmethod
    def from_charm(  # pylint: disable=too-many-arguments,too-many-locals
        cls,
        *,
        config: dict[str, bool | int | float | str | dict[str, str]],
        framework: str,
        framework_config: BaseModel,
        secret_storage: KeySecretStorage,
        integration_requirers: "IntegrationRequirers",
        base_url: str | None = None,
    ) -> "CharmState":
        """Initialize a new instance of the CharmState class from the associated charm.

        Args:
            config: The charm configuration.
            framework: The framework name.
            framework_config: The framework specific configurations.
            secret_storage: The secret storage manager associated with the charm.
            integration_requirers: The collection of integration requirers.
            base_url: Base URL for the service.

        Return:
            The CharmState instance created by the provided charm.

        Raises:
            CharmConfigInvalidError: If some parameter in invalid.
        """
        user_defined_config = {
            k.replace("-", "_"): v
            for k, v in config.items()
            if is_user_defined_config(k, framework)
        }
        user_defined_config = {
            k: v for k, v in user_defined_config.items() if k not in framework_config.dict().keys()
        }

        app_config_class = app_config_class_factory(framework)
        try:
            app_config_class(**user_defined_config)
        except ValidationError as exc:
            error_messages = build_validation_error_message(exc, underscore_to_dash=True)
            logger.error(error_messages.long)
            raise CharmConfigInvalidError(error_messages.short) from exc

        # 20250528 - OpenFGA library silently fails on Invalid relation data - if such
        # behavior is observed, raise an issue on their library to be more defensive about
        # relation data translation.
        # 20250528 - We need to dynamically handle the import of the errors these relation data
        # accessors can raise. The issue is with dynamically importing the libraries which might
        # be missing but is imported from, raising a NameError.
        try:
            integrations = IntegrationsState(
                databases_relation_data={
                    db: db_integration_data
                    for db, db_requirer in integration_requirers.databases.items()
                    if (db_integration_data := db_requirer.to_relation_data())
                },
                openfga=(
                    store_info
                    if (
                        integration_requirers.openfga
                        and (store_info := integration_requirers.openfga.get_store_info())
                    )
                    else None
                ),
                rabbitmq=(
                    integration_requirers.rabbitmq.get_relation_data()
                    if integration_requirers.rabbitmq
                    else None
                ),
                redis=(
                    integration_requirers.redis.to_relation_data()
                    if integration_requirers.redis
                    else None
                ),
                s3=(
                    integration_requirers.s3.to_relation_data()
                    if integration_requirers.s3
                    else None
                ),
                saml=(
                    integration_requirers.saml.to_relation_data()
                    if integration_requirers.saml
                    else None
                ),
                smtp=(
                    smtp_data
                    if (
                        integration_requirers.smtp
                        and (smtp_data := integration_requirers.smtp.get_relation_data())
                    )
                    else None
                ),
                tracing=(
                    integration_requirers.tracing.to_relation_data()
                    if integration_requirers.tracing
                    else None
                ),
            )
        except InvalidRelationDataError as exc:
            raise CharmConfigInvalidError(f"Invalid {exc.relation} relation data.") from exc
        peer_fqdns = None
        if secret_storage.is_initialized and (
            peer_unit_fqdns := secret_storage.get_peer_unit_fdqns()
        ):
            peer_fqdns = ",".join(peer_unit_fqdns)

        return cls(
            framework=framework,
            framework_config=framework_config.model_dump(exclude_none=True),
            user_defined_config=typing.cast(
                dict[str, str | int | bool | dict[str, str]], user_defined_config
            ),
            secret_key=(
                secret_storage.get_secret_key() if secret_storage.is_initialized else None
            ),
            is_secret_storage_ready=secret_storage.is_initialized,
            peer_fqdns=peer_fqdns,
            integrations=integrations,
            base_url=base_url,
        )

    @property
    def proxy(self) -> "ProxyConfig":
        """Get charm proxy information from juju charm environment.

        Returns:
            charm proxy information in the form of `ProxyConfig`.
        """
        http_proxy = os.environ.get("JUJU_CHARM_HTTP_PROXY")
        https_proxy = os.environ.get("JUJU_CHARM_HTTPS_PROXY")
        no_proxy = os.environ.get("JUJU_CHARM_NO_PROXY")
        return ProxyConfig(
            http_proxy=http_proxy if http_proxy else None,
            https_proxy=https_proxy if https_proxy else None,
            no_proxy=no_proxy,
        )

    @property
    def framework_config(self) -> dict[str, str | int | bool]:
        """Get the value of the framework application specific configuration.

        Returns:
            The value of the framework application specific configuration.
        """
        return self._framework_config

    @property
    def user_defined_config(self) -> dict[str, str | int | bool | dict[str, str]]:
        """Get the value of user-defined application configurations.

        Returns:
            The value of user-defined application configurations.
        """
        return self._user_defined_config

    @property
    def secret_key(self) -> str:
        """Return the application secret key stored in the SecretStorage.

        It's an error to read the secret key before SecretStorage is initialized.

        Returns:
            The application secret key stored in the SecretStorage.

        Raises:
            RuntimeError: raised when accessing application secret key before
                          secret storage is ready.
        """
        if self._secret_key is None:
            raise RuntimeError("access secret key before secret storage is ready")
        return self._secret_key

    @property
    def is_secret_storage_ready(self) -> bool:
        """Return whether the secret storage system is ready.

        Returns:
            Whether the secret storage system is ready.
        """
        return self._is_secret_storage_ready


@dataclass
class IntegrationRequirers:  # pylint: disable=too-many-instance-attributes
    """Collection of integration requirers.

    Attrs:
        databases: PaaSDatabaseRequires collection.
        rabbitmq: RabbitMQ requirer object.
        redis: Redis requirer object.
        s3: S3 requirer object.
        saml: Saml requirer object.
        tracing: TracingEndpointRequire object.
        smtp: Smtp requirer object.
        openfga: OpenFGA requirer object.
    """

    databases: dict[str, "PaaSDatabaseRequires"]
    openfga: "OpenFGARequires | None" = None
    rabbitmq: "RabbitMQRequires | None" = None
    redis: "PaaSRedisRequires | None" = None
    s3: "PaaSS3Requirer | None" = None
    saml: "PaaSSAMLRequirer | None" = None
    tracing: "PaaSTracingEndpointRequirer | None" = None
    smtp: "SmtpRequires | None" = None


@dataclass
class IntegrationsState:  # pylint: disable=too-many-instance-attributes
    """State of the integrations.

    This state is related to all the relations that can be optional, like databases, redis...

    Attrs:
        databases_relation_data: Map from interface_name to the database relation data.
        openfga: OpenFGA connection information from relation data.
        rabbitmq: RabbitMQ relation data.
        redis: The Redis connection info from redis lib.
        s3: S3 connection information from relation data.
        saml: SAML parameters.
        smtp: SMTP parameters.
        tracing: Tracing relation data.
    """

    databases_relation_data: dict[str, "PaaSDatabaseRelationData"] = field(default_factory=dict)
    openfga: "OpenfgaProviderAppData | None" = None
    rabbitmq: "PaaSRabbitMQRelationData | None" = None
    redis: "PaaSRedisRelationData | None" = None
    s3: "PaaSS3RelationData | None" = None
    saml: "PaaSSAMLRelationData | None" = None
    smtp: "SmtpRelationData | None" = None
    tracing: "PaaSTracingRelationData | None" = None


class ProxyConfig(BaseModel):
    """Configuration for network access through proxy.

    Attributes:
        http_proxy: The http proxy URL.
        https_proxy: The https proxy URL.
        no_proxy: Comma separated list of hostnames to bypass proxy.
    """

    http_proxy: str | None = Field(default=None, pattern="https?://.+")
    https_proxy: str | None = Field(default=None, pattern="https?://.+")
    no_proxy: typing.Optional[str] = None


def _create_config_attribute(option_name: str, option: dict) -> tuple[str, tuple]:
    """Create the configuration attribute.

    Args:
        option_name: Name of the configuration option.
        option: The configuration option data.

    Raises:
        ValueError: raised when the option type is not valid.

    Returns:
        A tuple constructed from attribute name and type.
    """
    option_name = option_name.replace("-", "_")
    optional = option.get("optional") is not False
    config_type_str = option.get("type")

    config_type: type[bool] | type[int] | type[float] | type[str] | type[dict]
    match config_type_str:
        case "boolean":
            config_type = bool
        case "int":
            config_type = int
        case "float":
            config_type = float
        case "string":
            config_type = str
        case "secret":
            config_type = dict
        case _:
            raise ValueError(f"Invalid option type: {config_type_str}.")

    type_tuple: tuple = (config_type, Field())
    if optional:
        type_tuple = (config_type | None, None)

    return (option_name, type_tuple)


def app_config_class_factory(framework: str) -> type[BaseModel]:
    """App config class factory.

    Args:
        framework: The framework name.

    Returns:
        Constructed app config class.
    """
    config_options = config_metadata(pathlib.Path(os.getcwd()))["options"]
    model_attributes = dict(
        _create_config_attribute(option_name, config_options[option_name])
        for option_name in config_options
        if is_user_defined_config(option_name, framework)
    )
    # mypy doesn't like the model_attributes dict
    return create_model("AppConfig", **model_attributes)  # type: ignore[call-overload]


def is_user_defined_config(option_name: str, framework: str) -> bool:
    """Check if a config option is user defined.

    Args:
        option_name: Name of the config option.
        framework: The framework name.

    Returns:
        True if user defined config options, false otherwise.
    """
    return not any(
        option_name.startswith(prefix) for prefix in (f"{framework}-", "webserver-", "app-")
    )
