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
from paas_charm.charm import PaasCharm
from paas_charm.framework import FrameworkConfig

if typing.TYPE_CHECKING:
    from charms.openfga_k8s.v1.openfga import OpenfgaProviderAppData
    from charms.smtp_integrator.v0.smtp import SmtpRelationData

    from paas_charm.databases import PaaSDatabaseRelationData
    from paas_charm.rabbitmq import PaaSRabbitMQRelationData
    from paas_charm.redis import PaaSRedisRelationData
    from paas_charm.s3 import PaaSS3RelationData
    from paas_charm.saml import PaaSSAMLRelationData

logger = logging.getLogger(__name__)

WORKLOAD_CONTAINER_NAME = "app"


class SpringBootConfig(FrameworkConfig):
    """Represent Spring Boot builtin configuration values.

    Attrs:
        port: port where the application is listening
        metrics_port: port where the metrics are collected
        metrics_path: path where the metrics are collected
        secret_key: a secret key that will be used for securely signing the session cookie
            and can be used for any other security related needs by your Flask application.
        model_config: Pydantic model configuration.
    """

    port: int = Field(alias="app-port", default=8080, gt=0)
    metrics_port: int | None = Field(alias="metrics-port", default=8080, gt=0)
    metrics_path: str | None = Field(
        alias="metrics-path", default="/actuator/prometheus", min_length=1
    )
    secret_key: str | None = Field(alias="app-secret-key", default=None, min_length=1)

    model_config = ConfigDict(extra="ignore")


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
    uri = relation_data.uris.split(",")[0]
    parsed = urlparse(uri)
    if database_name in ("mysql", "postgresql"):
        envvars = {
            "spring.datasource.url": f"jdbc:{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}",
            "spring.jpa.hibernate.ddl-auto": "none",
        }
        if parsed.username:
            envvars["spring.datasource.username"] = parsed.username
            # used for migrate.sh
            envvars[f"{database_name.upper()}_DB_USERNAME"] = parsed.username
        if parsed.password:
            envvars["spring.datasource.password"] = parsed.password
            # used for migrate.sh
            envvars[f"{database_name.upper()}_DB_PASSWORD"] = parsed.password
        if parsed.hostname:
            # used for migrate.sh
            envvars[f"{database_name.upper()}_DB_HOSTNAME"] = parsed.hostname
        db_name = parsed.path.removeprefix("/") if parsed.path else None
        if db_name is not None:
            envvars[f"{database_name.upper()}_DB_NAME"] = db_name
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
    return {}


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
    return {}


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
    """

    generate_db_env = staticmethod(generate_db_env)
    generate_openfga_env = staticmethod(generate_openfga_env)
    generate_rabbitmq_env = staticmethod(generate_rabbitmq_env)
    generate_redis_env = staticmethod(generate_redis_env)
    generate_s3_env = staticmethod(generate_s3_env)
    generate_saml_env = staticmethod(generate_saml_env)
    generate_smtp_env = staticmethod(generate_smtp_env)


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
            port=framework_config.port,
            base_dir=base_dir,
            app_dir=base_dir,
            state_dir=state_dir,
            service_name=framework_name,
            log_files=[],
            unit_name=self.unit.name,
            metrics_target=f"*:{framework_config.metrics_port}",
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
            framework_config_prefix="SERVER_",
        )
