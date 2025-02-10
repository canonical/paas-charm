# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""This module defines the CharmState class which represents the state of the charm."""
import logging
import os
import re
import typing
from dataclasses import dataclass, field
from typing import Optional, Type, TypeVar

from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.redis_k8s.v0.redis import RedisRequires
from pydantic import BaseModel, Extra, Field, ValidationError, ValidationInfo, field_validator

from paas_charm.databases import get_uri
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.rabbitmq import RabbitMQRequires
from paas_charm.secret_storage import KeySecretStorage
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

try:
    # the import is used for type hinting
    # pylint: disable=ungrouped-imports
    # pylint: disable=unused-import
    from charms.data_platform_libs.v0.s3 import S3Requirer
except ImportError:
    # we already logged it in charm.py
    pass

try:
    # the import is used for type hinting
    # pylint: disable=ungrouped-imports
    # pylint: disable=unused-import
    from charms.saml_integrator.v0.saml import SamlRequires
except ImportError:
    # we already logged it in charm.py
    pass

try:
    # the import is used for type hinting
    # pylint: disable=ungrouped-imports
    # pylint: disable=unused-import
    from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer
except ImportError:
    # we already logged it in charm.py
    pass


# too-many-instance-attributes is okay since we use a factory function to construct the CharmState
class CharmState:  # pylint: disable=too-many-instance-attributes
    """Represents the state of the charm.

    Attrs:
        framework_config: the value of the framework specific charm configuration.
        app_config: user-defined configurations for the application.
        secret_key: the charm managed application secret key.
        is_secret_storage_ready: whether the secret storage system is ready.
        proxy: proxy information.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        framework: str,
        is_secret_storage_ready: bool,
        app_config: dict[str, int | str | bool | dict[str, str]] | None = None,
        framework_config: dict[str, int | str] | None = None,
        secret_key: str | None = None,
        integrations: "IntegrationsState | None" = None,
        base_url: str | None = None,
    ):
        """Initialize a new instance of the CharmState class.

        Args:
            framework: the framework name.
            is_secret_storage_ready: whether the secret storage system is ready.
            app_config: User-defined configuration values for the application configuration.
            framework_config: The value of the framework application specific charm configuration.
            secret_key: The secret storage manager associated with the charm.
            integrations: Information about the integrations.
            base_url: Base URL for the service.
        """
        self.framework = framework
        self._framework_config = framework_config if framework_config is not None else {}
        self._app_config = app_config if app_config is not None else {}
        self._is_secret_storage_ready = is_secret_storage_ready
        self._secret_key = secret_key
        self.integrations = integrations or IntegrationsState()
        self.base_url = base_url

    @classmethod
    def from_charm(  # pylint: disable=too-many-arguments
        cls,
        *,
        config: dict[str, bool | int | float | str | dict[str, str]],
        framework: str,
        framework_config: BaseModel,
        secret_storage: KeySecretStorage,
        integration_requirers: "IntegrationRequirers",
        app_name: str | None = None,
        base_url: str | None = None,
    ) -> "CharmState":
        """Initialize a new instance of the CharmState class from the associated charm.

        Args:
            config: The charm configuration.
            framework: The framework name.
            framework_config: The framework specific configurations.
            secret_storage: The secret storage manager associated with the charm.
            integration_requirers: The collection of integration requirers.
            app_name: Name of the application.
            base_url: Base URL for the service.

        Return:
            The CharmState instance created by the provided charm.
        """
        app_config = {
            k.replace("-", "_"): v
            for k, v in config.items()
            if not any(k.startswith(prefix) for prefix in (f"{framework}-", "webserver-", "app-"))
        }
        app_config = {
            k: v for k, v in app_config.items() if k not in framework_config.dict().keys()
        }

        saml_relation_data = None
        if integration_requirers.saml and (
            saml_data := integration_requirers.saml.get_relation_data()
        ):
            saml_relation_data = saml_data.to_relation_data()

        integrations = IntegrationsState.build(
            app_name=app_name,
            redis_uri=(integration_requirers.redis.url if integration_requirers.redis else None),
            database_requirers=integration_requirers.databases,
            s3_connection_info=(
                integration_requirers.s3.get_s3_connection_info()
                if integration_requirers.s3
                else None
            ),
            saml_relation_data=saml_relation_data,
            rabbitmq_uri=(
                integration_requirers.rabbitmq.rabbitmq_uri()
                if integration_requirers.rabbitmq
                else None
            ),
            tracing_requirer=integration_requirers.tracing,
        )

        return cls(
            framework=framework,
            framework_config=framework_config.dict(exclude_none=True),
            app_config=typing.cast(dict[str, str | int | bool | dict[str, str]], app_config),
            secret_key=(
                secret_storage.get_secret_key() if secret_storage.is_initialized else None
            ),
            is_secret_storage_ready=secret_storage.is_initialized,
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
    def app_config(self) -> dict[str, str | int | bool | dict[str, str]]:
        """Get the value of user-defined application configurations.

        Returns:
            The value of user-defined application configurations.
        """
        return self._app_config

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
class IntegrationRequirers:
    """Collection of integration requirers.

    Attrs:
        databases: DatabaseRequires collection.
        redis: Redis requirer object.
        s3: S3 requirer object.
        saml: Saml requirer object.
        rabbitmq: RabbitMQ requirer object.
        tracing: TracingEndpointRequire object.
    """

    databases: dict[str, DatabaseRequires]
    rabbitmq: RabbitMQRequires | None = None
    redis: RedisRequires | None = None
    s3: "S3Requirer | None" = None
    saml: "SamlRequires | None" = None
    tracing: "TracingEndpointRequirer | None" = None


@dataclass
class IntegrationsState:
    """State of the integrations.

    This state is related to all the relations that can be optional, like databases, redis...

    Attrs:
        redis_uri: The redis uri provided by the redis charm.
        databases_uris: Map from interface_name to the database uri.
        s3_parameters: S3 parameters.
        saml_parameters: SAML parameters.
        rabbitmq_uri: RabbitMQ uri.
        tempo_parameters: Tracing parameters.
    """

    redis_uri: str | None = None
    databases_uris: dict[str, str] = field(default_factory=dict)
    s3_parameters: "S3Parameters | None" = None
    saml_parameters: "SamlParameters | None" = None
    rabbitmq_uri: str | None = None
    tempo_parameters: "TempoParameters | None" = None

    # This dataclass combines all the integrations, so it is reasonable that they stay together.
    @classmethod
    def build(  # pylint: disable=too-many-arguments
        cls,
        *,
        redis_uri: str | None,
        database_requirers: dict[str, DatabaseRequires],
        s3_connection_info: dict[str, str] | None,
        saml_relation_data: typing.MutableMapping[str, str] | None = None,
        rabbitmq_uri: str | None = None,
        tracing_requirer: "TracingEndpointRequirer | None" = None,
        app_name: str | None = None,
    ) -> "IntegrationsState":
        """Initialize a new instance of the IntegrationsState class.

        Args:
            app_name: Name of the application.
            redis_uri: The redis uri provided by the redis charm.
            database_requirers: All database requirers object declared by the charm.
            s3_connection_info: S3 connection info from S3 lib.
            saml_relation_data: Saml relation data from saml lib.
            rabbitmq_uri: RabbitMQ uri.
            tracing_requirer: The tracing relation data provided by the Tempo charm.

        Return:
            The IntegrationsState instance created.
        """
        s3_parameters = generate_relation_parameters(s3_connection_info, S3Parameters)
        saml_parameters = generate_relation_parameters(saml_relation_data, SamlParameters, True)
        tempo_data = {}
        if tracing_requirer and tracing_requirer.is_ready():
            tempo_data = {
                "service_name": app_name,
                "endpoint": tracing_requirer.get_endpoint(protocol="otlp_http"),
            }
        tempo_parameters = generate_relation_parameters(tempo_data, TempoParameters)

        # Workaround as the Redis library temporarily sends the port
        # as None while the integration is being created.
        if redis_uri is not None and re.fullmatch(r"redis://[^:/]+:None", redis_uri):
            redis_uri = None

        return cls(
            redis_uri=redis_uri,
            databases_uris={
                interface_name: uri
                for interface_name, requirers in database_requirers.items()
                if (uri := get_uri(requirers)) is not None
            },
            s3_parameters=s3_parameters,
            saml_parameters=saml_parameters,
            rabbitmq_uri=rabbitmq_uri,
            tempo_parameters=tempo_parameters,
        )


RelationParam = TypeVar("RelationParam", "SamlParameters", "S3Parameters", "TempoParameters")


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
        return parameter_type.parse_obj(relation_data)
    except ValidationError as exc:
        error_message = build_validation_error_message(exc)
        raise CharmConfigInvalidError(
            f"Invalid {parameter_type.__name__} configuration: {error_message}"
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

    endpoint: str | None = None
    service_name: str | None = None


class S3Parameters(BaseModel):
    """Configuration for accessing S3 bucket.

    Attributes:
        access_key: AWS access key.
        secret_key: AWS secret key.
        region: The region to connect to the object storage.
        storage_class: Storage Class for objects uploaded to the object storage.
        bucket: The bucket name.
        endpoint: The endpoint used to connect to the object storage.
        path: The path inside the bucket to store objects.
        s3_api_version: S3 protocol specific API signature.
        s3_uri_style: The S3 protocol specific bucket path lookup type. Can be "path" or "host".
        addressing_style: S3 protocol addressing style, can be "path" or "virtual".
        attributes: The custom metadata (HTTP headers).
        tls_ca_chain: The complete CA chain, which can be used for HTTPS validation.
    """

    access_key: str = Field(alias="access-key")
    secret_key: str = Field(alias="secret-key")
    region: Optional[str] = None
    storage_class: Optional[str] = Field(alias="storage-class", default=None)
    bucket: str
    endpoint: Optional[str] = None
    path: Optional[str] = None
    s3_api_version: Optional[str] = Field(alias="s3-api-version", default=None)
    s3_uri_style: Optional[str] = Field(alias="s3-uri-style", default=None)
    tls_ca_chain: Optional[list[str]] = Field(alias="tls-ca-chain", default=None)
    attributes: Optional[list[str]] = None

    @property
    def addressing_style(self) -> Optional[str]:
        """Translates s3_uri_style to AWS addressing_style."""
        if self.s3_uri_style == "host":
            return "virtual"
        # If None or "path", it does not change.
        return self.s3_uri_style


class SamlParameters(BaseModel, extra=Extra.allow):
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
