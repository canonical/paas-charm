# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Spring Boot Charm service."""

import logging
import pathlib
import typing
from urllib.parse import urlparse

import ops
from pydantic import ConfigDict, Field

from paas_charm.app import App, WorkloadConfig
from paas_charm.app import generate_db_env as base_generate_db_env
from paas_charm.charm import PaasCharm
from paas_charm.framework import FrameworkConfig

if typing.TYPE_CHECKING:
    from charms.openfga_k8s.v1.openfga import OpenfgaProviderAppData
    from charms.smtp_integrator.v0.smtp import SmtpRelationData

    from paas_charm.databases import PaaSDatabaseRelationData
    from paas_charm.oauth import PaaSOAuthRelationData
    from paas_charm.rabbitmq import PaaSRabbitMQRelationData
    from paas_charm.redis import PaaSRedisRelationData
    from paas_charm.s3 import PaaSS3RelationData
    from paas_charm.saml import PaaSSAMLRelationData
    from paas_charm.tracing import PaaSTracingRelationData

logger = logging.getLogger(__name__)

WORKLOAD_CONTAINER_NAME = "app"


class SpringBootConfig(FrameworkConfig):
    """Represent Spring Boot builtin configuration values.

    Attrs:
        server_port: port where the application is listening
        management_server_port: port where the metrics are collected
        metrics_path: path where the metrics are collected
        secret_key: a secret key that will be used for securely signing the session cookie
            and can be used for any other security related needs by your Flask application.
        model_config: Pydantic model configuration.
    """

    server_port: int = Field(alias="app-port", default=8080, gt=0)
    management_server_port: int | None = Field(alias="metrics-port", default=8080, gt=0)
    metrics_path: str | None = Field(
        alias="metrics-path", default="/actuator/prometheus", min_length=1
    )
    secret_key: str | None = Field(alias="app-secret-key", default=None, min_length=1)

    model_config = ConfigDict(extra="ignore")


def generate_prometheus_env(workload_config: WorkloadConfig) -> dict[str, str]:
    """Generate environment variable from WorkloadConfig.

    Args:
        workload_config: The charm workload config.

    Returns:
        Default Prometheus environment mappings.
    """
    if not workload_config.metrics_path:
        return {}
    metrics_path_list = [part for part in workload_config.metrics_path.split("/") if part]
    return {
        "management.endpoints.web.exposure.include": "prometheus",
        "management.endpoints.web.base-path": f"/{'/'.join(metrics_path_list[:-1])}",
        "management.endpoints.web.path-mapping.prometheus": metrics_path_list[-1],
    }


def generate_oauth_env(
    framework: str,  # pylint: disable=unused-argument
    relation_data: "PaaSOAuthRelationData | None" = None,
) -> dict[str, str]:
    """Generate environment variable from PaaSOAuthRelationData.

    Args:
        framework: The charm framework name.
        relation_data: The charm Oauth integration relation data.

    Returns:
        Default Oauth environment mappings if PaaSOAuthRelationData is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}

    provider_name = relation_data.provider_name
    return {
        f"spring.security.oauth2.client.registration.{provider_name}.client-id": relation_data.client_id,
        f"spring.security.oauth2.client.registration.{provider_name}.client-secret": relation_data.client_secret,
        f"spring.security.oauth2.client.registration.{provider_name}.redirect-uri": relation_data.redirect_uri,
        f"spring.security.oauth2.client.registration.{provider_name}.scope": ",".join(
            relation_data.scopes.split()
        ),
        f"spring.security.oauth2.client.registration.{provider_name}.user-name-attribute": relation_data.user_name_attribute,
        f"spring.security.oauth2.client.provider.{provider_name}.authorization-uri": relation_data.authorization_endpoint,
        f"spring.security.oauth2.client.provider.{provider_name}.issuer-uri": relation_data.issuer_url,
        f"spring.security.oauth2.client.provider.{provider_name}.jwk-set-uri": relation_data.jwks_endpoint,
        f"spring.security.oauth2.client.provider.{provider_name}.token-uri": relation_data.token_endpoint,
        f"spring.security.oauth2.client.provider.{provider_name}.user-info-uri": relation_data.userinfo_endpoint,
        f"spring.security.oauth2.client.provider.{provider_name}.user-name-attribute": relation_data.user_name_attribute,
        f"spring.security.oauth2.client.registration.{provider_name}.authorization-grant-type": "authorization_code",
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
    envvars = base_generate_db_env(database_name, relation_data)
    if not relation_data:
        return envvars
    uri = relation_data.uris.split(",")[0]
    parsed = urlparse(uri)
    if database_name in ("mysql", "postgresql"):
        envvars.update(
            {
                "spring.datasource.url": f"jdbc:{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}",
                "spring.jpa.hibernate.ddl-auto": "none",
            }
        )
        if parsed.username:
            envvars["spring.datasource.username"] = parsed.username
        if parsed.password:
            envvars["spring.datasource.password"] = parsed.password
        return envvars
    if database_name == "mongodb":
        return {"spring.data.mongodb.uri": uri}
    logger.warning(
        "Unknown database relation %s, no environment variables generated", database_name
    )
    return {}


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
            ("openfga.store-id", relation_data.store_id),
            ("openfga.credentials.method", "API_TOKEN"),
            ("openfga.credentials.config.api-token", relation_data.token),
            ("openfga.api-url", relation_data.http_api_url),
        )
        if v is not None
    }


def generate_rabbitmq_env(
    relation_data: "PaaSRabbitMQRelationData | None" = None,
) -> dict[str, str]:
    """Generate environment variable from RabbitMQ relation data.

    Args:
        relation_data: The charm Redis integration relation data.

    Returns:
        Redis environment mappings if Redis relation data is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    return {
        "spring.rabbitmq.virtual-host": relation_data.vhost,
        "spring.rabbitmq.username": relation_data.username,
        "spring.rabbitmq.password": relation_data.password,
        "spring.rabbitmq.host": relation_data.hostname,
        "spring.rabbitmq.port": str(relation_data.port),
    }


def generate_redis_env(
    relation_data: "PaaSRedisRelationData | None" = None,
) -> dict[str, str]:
    """Generate environment variable from Redis relation data.

    Args:
        relation_data: The charm Redis integration relation data.

    Returns:
        Redis environment mappings if Redis relation data is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    parsed = urlparse(str(relation_data.url))
    env = {"spring.data.redis.url": str(relation_data.url)}
    if parsed.hostname:
        env["spring.data.redis.host"] = parsed.hostname
    if parsed.port:
        env["spring.data.redis.port"] = str(parsed.port)
    if parsed.username:
        env["spring.data.redis.username"] = parsed.username
    if parsed.password:
        env["spring.data.redis.password"] = parsed.password

    return env


def generate_s3_env(relation_data: "PaaSS3RelationData | None" = None) -> dict[str, str]:
    """Generate environment variable from S3 relation data.

    Args:
        relation_data: The charm S3 integration relation data.

    Returns:
        S3 environment mappings if S3 relation data is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}
    env = {
        "spring.cloud.aws.credentials.accessKey": relation_data.access_key,
        "spring.cloud.aws.credentials.secretKey": relation_data.secret_key,
        "spring.cloud.aws.s3.bucket": relation_data.bucket,
    }
    if relation_data.region:
        env["spring.cloud.aws.region.static"] = relation_data.region
    if relation_data.endpoint:
        env["spring.cloud.aws.s3.endpoint"] = relation_data.endpoint

    return env


def generate_saml_env(
    relation_data: "PaaSSAMLRelationData | None" = None,
) -> dict[str, str]:
    """Generate environment variable from SAML relation data.

    Args:
        relation_data: The charm SAML integration relation data.

    Returns:
        SAML environment mappings if SAML relation data is available, empty
        dictionary otherwise.
    """
    if not relation_data:
        return {}

    env = {
        "spring.security.saml2.relyingparty.registration.testentity.assertingparty.metadata-uri": relation_data.metadata_url.unicode_string(),
        "spring.security.saml2.relyingparty.registration.testentity.entity-id": relation_data.entity_id,
    }
    if relation_data.single_sign_on_redirect_url:
        env[
            "spring.security.saml2.relyingparty.registration.testentity.assertingparty.singlesignin.url"
        ] = relation_data.single_sign_on_redirect_url

    if relation_data.signing_certificate:
        env[
            "spring.security.saml2.relyingparty.registration.testentity.assertingparty.verification.credentials[0].certificate-location"
        ] = "file:/app/saml.cert"

    return env


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
        "spring.mail.host": relation_data.host,
        "spring.mail.port": relation_data.port,
        "spring.mail.username": f"{relation_data.user}@{relation_data.domain}",
        "spring.mail.password": relation_data.password,
        "spring.mail.properties.mail.smtp.auth": relation_data.auth_type.value,
        "spring.mail.properties.mail.smtp.starttls.enable": str(
            relation_data.transport_security.value == "starttls"
        ).lower(),
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
        return {
            "OTEL_TRACES_EXPORTER": "none",
            "OTEL_METRICS_EXPORTER": "none",
            "OTEL_LOGS_EXPORTER": "none",
        }
    return {
        k: v
        for k, v in (
            ("OTEL_SERVICE_NAME", relation_data.service_name),
            ("OTEL_EXPORTER_OTLP_ENDPOINT", str(relation_data.endpoint)),
        )
        if v is not None
    }


class SpringBootApp(App):
    """Spring Boot application with custom environment variable mappers.

    Attributes:
        generate_db_env: Maps database connection information to environment variables.
        generate_openfga_env: Maps OpenFGA connection information to environment variables.
        generate_rabbitmq_env: Maps RabbitMQ connection information to environment variables.
        generate_redis_env: Maps Redis connection information to environment variables.
        generate_s3_env: Maps S3 connection information to environment variables.
        generate_saml_env: Maps SAML connection information to environment variables.
        generate_smtp_env: Maps STMP connection information to environment variables.
        generate_tempo_env: Maps Tracing connection information to environment variables.
        generate_prometheus_env: Maps Prometheus connection information to environment variables.
        generate_oauth_env: Maps Oauth connection information to environment variables.
    """

    generate_db_env = staticmethod(generate_db_env)
    generate_openfga_env = staticmethod(generate_openfga_env)
    generate_rabbitmq_env = staticmethod(generate_rabbitmq_env)
    generate_redis_env = staticmethod(generate_redis_env)
    generate_s3_env = staticmethod(generate_s3_env)
    generate_saml_env = staticmethod(generate_saml_env)
    generate_smtp_env = staticmethod(generate_smtp_env)
    generate_tempo_env = staticmethod(generate_tempo_env)
    generate_prometheus_env = staticmethod(generate_prometheus_env)
    generate_oauth_env = staticmethod(generate_oauth_env)

    def gen_environment(self) -> dict[str, str]:
        """Generate a environment dictionary from the charm configurations.

        Adds to the base environment variables specific ones for the Spring Boot framework.

        Returns:
            A dictionary representing the application environment variables.
        """
        env = super().gen_environment()
        # Required because of the strip prefix in the ingress configuration.
        env["server.forward-headers-strategy"] = "framework"
        return env


class Charm(PaasCharm):
    """Spring Boot Charm service.

    Attrs:
        framework_config_class: Base class for framework configuration.
    """

    framework_config_class = SpringBootConfig

    def __init__(self, framework: ops.Framework) -> None:
        """Initialize the SpringBootConfig charm.

        Args:
            framework: operator framework.
        """
        super().__init__(framework=framework, framework_name="spring-boot")

    @property
    def _workload_config(self) -> WorkloadConfig:
        """Return an WorkloadConfig instance."""
        framework_name = self._framework_name
        base_dir = pathlib.Path("/app")
        state_dir = base_dir / "state"
        framework_config = typing.cast(SpringBootConfig, self.get_framework_config())

        return WorkloadConfig(
            framework=framework_name,
            container_name=WORKLOAD_CONTAINER_NAME,
            port=framework_config.server_port,
            base_dir=base_dir,
            app_dir=base_dir,
            state_dir=state_dir,
            service_name=framework_name,
            log_files=[],
            unit_name=self.unit.name,
            metrics_target=f"*:{framework_config.management_server_port}",
            metrics_path=framework_config.metrics_path,
        )

    def _create_app(self) -> App:
        """Build a App instance.

        Returns:
            A new App instance.
        """
        charm_state = self._create_charm_state()
        if charm_state.integrations.saml and charm_state.integrations.saml.signing_certificate:
            cert = charm_state.integrations.saml.signing_certificate
            if not cert.startswith("-----BEGIN CERTIFICATE-----"):
                cert = f"-----BEGIN CERTIFICATE-----\n{cert}\n-----END CERTIFICATE-----"
            self._container.push(self._workload_config.app_dir / "saml.cert", cert)

        return SpringBootApp(
            container=self._container,
            charm_state=charm_state,
            workload_config=self._workload_config,
            database_migration=self._database_migration,
            framework_config_prefix="",
        )

    def get_cos_dir(self) -> str:
        """Return the directory with COS related files.

        Returns:
            Return the directory with COS related files.
        """
        return str((pathlib.Path(__file__).parent / "cos").absolute())
