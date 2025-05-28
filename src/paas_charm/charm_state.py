# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""This module defines the CharmState class which represents the state of the charm."""
import logging
import os
import pathlib
import typing
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Type, TypeVar

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    ValidationInfo,
    create_model,
    field_validator,
)

from paas_charm.databases import PaaSDatabaseRelationData, PaaSDatabaseRequires
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.rabbitmq import RabbitMQRequires
from paas_charm.redis import PaaSRedisRelationData, PaaSRedisRequires
from paas_charm.secret_storage import KeySecretStorage
from paas_charm.utils import build_validation_error_message, config_metadata

if typing.TYPE_CHECKING:
    from paas_charm.rabbitmq import PaaSRabbitMQRelationData

logger = logging.getLogger(__name__)

try:
    # the import is used for type hinting
    # pylint: disable=ungrouped-imports
    # pylint: disable=unused-import
    from paas_charm.s3 import InvalidS3RelationDataError, PaaSS3RelationData, PaaSS3Requirer
except ImportError:
    # we already logged it in charm.py
    pass

try:
    # the import is used for type hinting
    # pylint: disable=ungrouped-imports
    # pylint: disable=unused-import
    from paas_charm.saml import (
        InvalidSAMLRelationDataError,
        PaaSSAMLRelationData,
        PaaSSAMLRequirer,
    )
except ImportError:
    # we already logged it in charm.py
    pass

try:
    # the import is used for type hinting
    # pylint: disable=ungrouped-imports
    # pylint: disable=unused-import
    from paas_charm.tempo import PaaSTempoRelationData, PaaSTracingEndpointRequirer
except ImportError:
    # we already logged it in charm.py
    pass

try:
    # the import is used for type hinting
    # pylint: disable=ungrouped-imports
    # pylint: disable=unused-import
    from charms.smtp_integrator.v0.smtp import SmtpRelationData, SmtpRequires
except ImportError:
    # we already logged it in charm.py
    pass

try:
    # the import is used for type hinting
    # pylint: disable=ungrouped-imports
    # pylint: disable=unused-import
    from charms.openfga_k8s.v1.openfga import OpenfgaProviderAppData, OpenFGARequires
except ImportError:
    # we already logged it in charm.py
    pass


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

        # 2025/04/15 When done ejecting IntegrationParameters, we should remove the build function
        # and just wrap the PydanticObjects from IntegrationRequirer libs into the
        # IntegrationState, without the build function. See integration_requirers.s3.
        try:
            integrations = IntegrationsState.build(
                redis_relation_data=(
                    integration_requirers.redis.to_relation_data()
                    if integration_requirers.redis
                    else None
                ),
                databases_relation_data={
                    db: db_integration_data
                    for db, db_requirer in integration_requirers.databases.items()
                    if (db_integration_data := db_requirer.to_relation_data())
                },
                s3_relation_data=(
                    integration_requirers.s3.to_relation_data()
                    if integration_requirers.s3
                    else None
                ),
                saml_relation_data=(
                    integration_requirers.saml.to_relation_data()
                    if integration_requirers.saml
                    else None
                ),
                rabbitmq_relation_data=(
                    integration_requirers.rabbitmq.get_relation_data()
                    if integration_requirers.rabbitmq
                    else None
                ),
                tempo_relation_data=(
                    integration_requirers.tracing.to_relation_data()
                    if integration_requirers.tracing
                    else None
                ),
                smtp_relation_data=(
                    smtp_data
                    if (
                        integration_requirers.smtp
                        and (smtp_data := integration_requirers.smtp.get_relation_data())
                    )
                    else None
                ),
                openfga_relation_data=(
                    store_info
                    if (
                        integration_requirers.openfga
                        and (store_info := integration_requirers.openfga.get_store_info())
                    )
                    else None
                ),
            )
            peer_fqdns = None
            if secret_storage.is_initialized and (
                peer_unit_fqdns := secret_storage.get_peer_unit_fdqns()
            ):
                peer_fqdns = ",".join(peer_unit_fqdns)
        except InvalidS3RelationDataError as exc:
            raise CharmConfigInvalidError("Invalid S3 relation data") from exc
        except InvalidSAMLRelationDataError as exc:
            raise CharmConfigInvalidError("Invalid SAML relation data") from exc

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

    databases: dict[str, PaaSDatabaseRequires]
    rabbitmq: RabbitMQRequires | None = None
    redis: PaaSRedisRequires | None = None
    s3: "PaaSS3Requirer | None" = None
    saml: "PaaSSAMLRequirer | None" = None
    tracing: "PaaSTracingEndpointRequirer | None" = None
    smtp: "SmtpRequires | None" = None
    openfga: "OpenFGARequires | None" = None


@dataclass
class IntegrationsState:  # pylint: disable=too-many-instance-attributes
    """State of the integrations.

    This state is related to all the relations that can be optional, like databases, redis...

    Attrs:
        databases_relation_data: Map from interface_name to the database relation data.
        openfga: OpenFGA connection information from relation data.
        rabbitmq: RabbitMQ relation data.
        redis_relation_data: The Redis connection info from redis lib.
        s3: S3 connection information from relation data.
        saml: SAML parameters.
        smtp: Smtp parameters.
        tempo: Tracing relation data.
    """

    databases_relation_data: dict[str, PaaSDatabaseRelationData] = field(default_factory=dict)
    openfga: "OpenfgaProviderAppData | None" = None
    rabbitmq: "PaaSRabbitMQRelationData | None" = None
    redis_relation_data: PaaSRedisRelationData | None = None
    s3: "PaaSS3RelationData | None" = None
    saml: "PaaSSAMLRelationData | None" = None
    smtp: "SmtpRelationData | None" = None
    tempo: "PaaSTempoRelationData | None" = None

    # This dataclass combines all the integrations, so it is reasonable that they stay together.
    @classmethod
    def build(  # pylint: disable=too-many-arguments
        cls,
        *,
        databases_relation_data: dict[str, PaaSDatabaseRelationData],
        openfga_relation_data: "OpenfgaProviderAppData | None" = None,
        rabbitmq_relation_data: "PaaSRabbitMQRelationData | None" = None,
        redis_relation_data: PaaSRedisRelationData | None,
        s3_relation_data: "PaaSS3RelationData | None" = None,
        saml_relation_data: "PaaSSAMLRelationData| None" = None,
        smtp_relation_data: "SmtpRelationData | None" = None,
        tempo_relation_data: "PaaSTempoRelationData | None" = None,
    ) -> "IntegrationsState":
        """Initialize a new instance of the IntegrationsState class.

        Args:
            databases_relation_data: All database relation data from charm integration.
            openfga_relation_data: OpenFGA relation data from openfga lib.
            rabbitmq_relation_data: RabbitMQ relation data.
            redis_relation_data: The Redis connection info from redis lib.
            s3_relation_data: S3 relation data from S3 lib.
            saml_relation_data: Saml relation data from saml lib.
            smtp_relation_data: Smtp relation data from smtp lib.
            tempo_relation_data: The tracing relation data provided by the Tempo charm.

        Return:
            The IntegrationsState instance created.
        """
        return cls(
            databases_relation_data=databases_relation_data,
            openfga=openfga_relation_data,
            rabbitmq=rabbitmq_relation_data,
            redis_relation_data=redis_relation_data,
            s3=s3_relation_data,
            saml=saml_relation_data,
            smtp=smtp_relation_data,
            tempo=tempo_relation_data,
        )


RelationParam = TypeVar("RelationParam", "SamlParameters", "SmtpParameters", "OpenfgaParameters")


def generate_relation_parameters(
    relation_data: dict[str, str] | typing.MutableMapping[str, str] | None,
    parameter_type: Type[RelationParam],
    support_empty: bool = False,
) -> RelationParam | None:
    """Generate relation parameter class from relation data.

    Args:
        relation_data: Relation data.
        parameter_type: Parameter type to use.
        support_empty: Support empty relation data.

    Return:
        Parameter instance created.

    Raises:
        CharmConfigInvalidError: If some parameter in invalid.
    """
    if not support_empty and not relation_data:
        return None
    if relation_data is None:
        return None

    try:
        return parameter_type.model_validate(relation_data)
    except ValidationError as exc:
        error_messages = build_validation_error_message(exc)
        logger.error(error_messages.long)
        raise CharmConfigInvalidError(
            f"Invalid {parameter_type.__name__}: {error_messages.short}"
        ) from exc


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


class TempoParameters(BaseModel):
    """Configuration for accessing Tempo service.

    Attributes:
        endpoint: Tempo endpoint URL to send the traces.
        service_name: Tempo service name for the workload.
    """

    endpoint: str = Field(alias="endpoint")
    service_name: str = Field(alias="service_name")


class SamlParameters(BaseModel, extra="allow"):
    """Configuration for accessing SAML.

    Attributes:
        entity_id: Entity Id of the SP.
        metadata_url: URL for the metadata for the SP.
        signing_certificate: Signing certificate for the SP.
        single_sign_on_redirect_url: Sign on redirect URL for the SP.
    """

    entity_id: str
    metadata_url: str
    signing_certificate: str = Field(alias="x509certs")
    single_sign_on_redirect_url: str = Field(alias="single_sign_on_service_redirect_url")

    @field_validator("signing_certificate")
    @classmethod
    def validate_signing_certificate_exists(cls, certs: str, _: ValidationInfo) -> str:
        """Validate that at least a certificate exists in the list of certificates.

        It is a prerequisite that the fist certificate is the signing certificate,
        otherwise this method would return a wrong certificate.

        Args:
            certs: Original x509certs field

        Returns:
            The validated signing certificate

        Raises:
            ValueError: If there is no certificate.
        """
        certificate = certs.split(",")[0]
        if not certificate:
            raise ValueError("Missing x509certs. There should be at least one certificate.")
        return certificate


class TransportSecurity(str, Enum):
    """Represent the transport security values.

    Attributes:
        NONE: none
        STARTTLS: starttls
        TLS: tls
    """

    NONE = "none"
    STARTTLS = "starttls"
    TLS = "tls"


class AuthType(str, Enum):
    """Represent the auth type values.

    Attributes:
        NONE: none
        NOT_PROVIDED: not_provided
        PLAIN: plain
    """

    NONE = "none"
    NOT_PROVIDED = "not_provided"
    PLAIN = "plain"


class SmtpParameters(BaseModel, extra="allow"):
    """Represent the SMTP relation data.

    Attributes:
        host: The hostname or IP address of the outgoing SMTP relay.
        port: The port of the outgoing SMTP relay.
        user: The SMTP AUTH user to use for the outgoing SMTP relay.
        password: The SMTP AUTH password to use for the outgoing SMTP relay.
        password_id: The secret ID where the SMTP AUTH password for the SMTP relay is stored.
        auth_type: The type used to authenticate with the SMTP relay.
        transport_security: The security protocol to use for the outgoing SMTP relay.
        domain: The domain used by the emails sent from SMTP relay.
        skip_ssl_verify: Specifies if certificate trust verification is skipped in the SMTP relay.
    """

    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65536)
    user: str | None = None
    password: str | None = None
    password_id: str | None = None
    auth_type: AuthType | None = None
    transport_security: TransportSecurity | None = None
    domain: str | None = None
    skip_ssl_verify: str | None = None

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, auth_type: AuthType, _: ValidationInfo) -> AuthType | None:
        """Turn auth_type type into None if its "none".

        Args:
            auth_type: Authentication type.

        Returns:
            The validated Authentication type.
        """
        if auth_type == AuthType.NONE:
            return None
        return auth_type

    @field_validator("transport_security")
    @classmethod
    def validate_transport_security(
        cls, transport_security: TransportSecurity, _: ValidationInfo
    ) -> TransportSecurity | None:
        """Turn transport_security into None if its "none".

        Args:
            transport_security: security protocol.

        Returns:
            The validated security protocol.
        """
        if transport_security == TransportSecurity.NONE:
            return None
        return transport_security


class OpenfgaParameters(BaseModel, extra="allow"):
    """Represent the OpenFGA relation data.

    Attributes:
        store_id: The store id to use on the OpenFGA server.
        token: The token to use for api authentication.
        grpc_api_url: The gRPC api url of the OpenFGA server.
        http_api_url: The HTTP api url of the OpenFGA server.
    """

    store_id: str | None = None
    token: str | None = None
    grpc_api_url: str = Field(...)
    http_api_url: str = Field(...)


def store_info_to_relation_data(store_info: "OpenfgaProviderAppData") -> Dict[str, str]:
    """Convert store info to relation data.

    Args:
        store_info: Store info as returned from openfga lib.

    Returns:
        A dict containing relation info.
    """
    result = {
        "grpc_api_url": str(store_info.grpc_api_url),
        "http_api_url": str(store_info.http_api_url),
    }
    if store_info.store_id is not None:
        result["store_id"] = str(store_info.store_id)
    if store_info.token is not None:
        result["token"] = str(store_info.token)
    return result


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
