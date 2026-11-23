# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for reading and validating the paas-config.yaml configuration file."""

import enum
import logging
import pathlib
import typing
from collections import Counter

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from paas_charm import env_templates
from paas_charm.exceptions import PaasConfigError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "paas-config.yaml"


class LoggingFormat(str, enum.Enum):
    """Valid values for the ``framework_logging_format`` paas-config option.

    Inherits from ``str`` so that Pydantic can coerce plain YAML strings (e.g.
    ``"json"``) into enum members, and so that enum values compare equal to
    their string equivalents.

    Attributes:
        NONE: No structured logging format; use the framework default.
        JSON: Structured JSON logging using OTEL semantic conventions.
    """

    NONE = "none"
    JSON = "json"


# Mapping of LoggingFormat to the set of frameworks that support it.
FRAMEWORKS_SUPPORTING_LOGGING_FORMAT: dict[LoggingFormat, set[str]] = {
    LoggingFormat.JSON: {"fastapi", "flask", "django"},
}


class StaticConfig(BaseModel):
    """Prometheus static configuration for scrape targets.

    Attributes:
        targets: List of target hosts to scrape (e.g., ["*:8000", "localhost:9090"]).
                 Supports @scheduler placeholder for targeting scheduler unit (unit 0).
        labels: Optional labels to assign to all metrics from these targets.
        model_config: Pydantic model configuration.
    """

    targets: typing.List[str] = Field(description="List of target hosts to scrape")
    labels: typing.Dict[str, str] | None = Field(
        default=None, description="Labels assigned to all metrics scraped from the targets"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("targets")
    @classmethod
    def validate_scheduler_format(cls, targets: typing.List[str]) -> typing.List[str]:
        """Validate @scheduler placeholder format.

        Args:
            targets: List of target strings to validate.

        Returns:
            The validated targets list.

        Raises:
            ValueError: If @scheduler format is invalid (must be @scheduler:PORT).
        """
        for target in targets:
            if target.startswith("@scheduler"):
                if not target.startswith("@scheduler:"):
                    raise ValueError(
                        f"Invalid @scheduler format '{target}': must include port (@scheduler:PORT)"
                    )
                port_str = target.split(":", 1)[1]
                if not port_str or not port_str.isdigit():
                    raise ValueError(f"Invalid @scheduler format '{target}': port must be numeric")
        return targets


class ScrapeConfig(BaseModel):
    """Prometheus scrape job configuration.

    Attributes:
        job_name: Job name assigned to scraped metrics.
        metrics_path: HTTP resource path on which to fetch metrics from targets.
        static_configs: List of statically configured targets for this job.
        model_config: Pydantic model configuration.
    """

    job_name: str = Field(description="Job name assigned to scraped metrics")
    metrics_path: str = Field(
        default="/metrics",
        description="HTTP resource path on which to fetch metrics",
    )
    static_configs: typing.List[StaticConfig] = Field(
        description="List of labeled statically configured targets for this job"
    )

    model_config = ConfigDict(extra="forbid")


class PrometheusConfig(BaseModel):
    """Prometheus configuration section.

    Attributes:
        scrape_configs: List of scrape job configurations.
        model_config: Pydantic model configuration.
    """

    scrape_configs: typing.List[ScrapeConfig] | None = Field(
        default=None, description="List of scrape job configurations"
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_unique_job_names(self) -> "PrometheusConfig":
        """Validate that all job_names are unique.

        Returns:
            The validated PrometheusConfig instance.

        Raises:
            ValueError: If duplicate job_names are found.
        """
        if not self.scrape_configs:
            return self

        job_names = Counter(sc.job_name for sc in self.scrape_configs)
        duplicates = [name for name, count in job_names.items() if count > 1]

        if duplicates:
            raise ValueError(
                f"Duplicate job_name values found in prometheus.scrape_configs: "
                f"{', '.join(sorted(duplicates))}. Each job must have a unique name."
            )

        return self


class EnvVarConfig(BaseModel):
    """Environment variable name for a non-secret charm configuration option.

    Attributes:
        env_var: Complete environment variable name.
        model_config: Pydantic model configuration.
    """

    env_var: str = Field(alias="env-var")
    model_config = ConfigDict(extra="forbid", strict=True)


class SecretEnvVarsConfig(BaseModel):
    """Environment variable names for a secret charm configuration option.

    Attributes:
        secret_env_vars: Secret content keys mapped to complete environment variable names.
        model_config: Pydantic model configuration.
    """

    secret_env_vars: dict[str, str] = Field(alias="secret-env-vars")
    model_config = ConfigDict(extra="forbid", strict=True)


class ConfigOptions(BaseModel):
    """Settings for existing charm configuration options.

    Attributes:
        options: Exact charm configuration option names mapped to their settings.
        model_config: Pydantic model configuration.
    """

    options: dict[str, EnvVarConfig | SecretEnvVarsConfig] = Field(default_factory=dict)
    model_config = ConfigDict(extra="forbid", strict=True)

    @model_validator(mode="after")
    def validate_destinations(self) -> "ConfigOptions":
        """Validate destination names and reject ambiguous mappings.

        Returns:
            The validated configuration.

        Raises:
            ValueError: If a destination is invalid or used by multiple sources.
        """
        destinations: dict[str, str] = {}
        for option, mapping in self.options.items():  # pylint: disable=no-member
            entries = (
                mapping.secret_env_vars.items()
                if isinstance(mapping, SecretEnvVarsConfig)
                else [(None, mapping.env_var)]
            )
            for key, destination in entries:
                source = option if key is None else f"{option}.{key}"
                if not destination or "\0" in destination or "=" in destination:
                    raise ValueError(
                        f"Invalid environment variable name for {source!r} in {CONFIG_FILE_NAME}: "
                        "destination names must be non-empty and contain neither '=' nor NUL"
                    )
                if destination in destinations:
                    raise ValueError(
                        f"Environment variable {destination!r} is mapped from both "
                        f"{destinations[destination]!r} and {source!r}"
                    )
                destinations[destination] = source
        return self

    def validate_sources(self, options: dict, unsupported: set[str]) -> None:
        """Validate sources against charm configuration metadata.

        Args:
            options: Charm configuration option metadata.
            unsupported: Option names without mappable environment outputs.

        Raises:
            PaasConfigError: If an option is unknown, unsupported, or has the wrong mapping shape.
        """
        for option, mapping in self.options.items():  # pylint: disable=no-member
            if option not in options:
                raise PaasConfigError(
                    f"{CONFIG_FILE_NAME}: config.options references unknown "
                    f"charm configuration option {option!r}"
                )
            if option in unsupported:
                raise PaasConfigError(
                    f"{CONFIG_FILE_NAME}: config.options cannot map option {option!r}: "
                    "it has no configuration-derived environment output"
                )
            normalized = option.replace("-", "_")
            for other in options:
                if other != option and other.replace("-", "_") == normalized:
                    raise PaasConfigError(
                        f"{CONFIG_FILE_NAME}: config.options cannot distinguish charm configuration "
                        f"options {option!r} and {other!r}: hyphens and underscores are "
                        "treated identically internally"
                    )
            is_secret = options[option]["type"] == "secret"
            if is_secret != isinstance(mapping, SecretEnvVarsConfig):
                expected = "secret-env-vars" if is_secret else "env-var"
                raise PaasConfigError(
                    f"{CONFIG_FILE_NAME}: config.options.{option} must use {expected!r}"
                )


class OAuthRelationConfig(BaseModel):
    """Static settings that the charm sends to an OAuth provider.

    Attributes:
        redirect_path: Path component of the redirect URI, appended to the application base URL.
        scopes: Scopes requested from the provider. Must include ``openid``.
        model_config: Pydantic model configuration.
    """

    redirect_path: str = Field(default="/callback", alias="redirect-path", min_length=1)
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)

    @field_validator("scopes")
    @classmethod
    def _validate_scopes(cls, scopes: list[str]) -> list[str]:
        """Validate the requested scopes.

        Args:
            scopes: The requested scopes.

        Returns:
            The validated scopes.

        Raises:
            ValueError: If a scope is empty or contains whitespace, or ``openid`` is missing.
        """
        for scope in scopes:
            if not scope or any(char.isspace() for char in scope):
                raise ValueError(
                    f"invalid OAuth scope {scope!r}: must be non-empty without spaces"
                )
        if "openid" not in scopes:
            raise ValueError("scopes must include 'openid'")
        return scopes


class PaasConfig(BaseModel):
    """Configuration from paas-config.yaml file.

    Attributes:
        prometheus: Prometheus-related configuration.
        framework_logging_format: Structured logging format for the framework server.
            Defaults to ``LoggingFormat.NONE`` (framework default logging).
            ``LoggingFormat.JSON`` ("json") is supported for FastAPI, Flask, and Django.
        model_config: Pydantic model configuration.
        port: Optional override for the port on which the application server listens.
        metrics_port: Optional override for the port on which the application serves metrics.
        metrics_path: Optional override for the path on which the application serves metrics.
        config: Settings for existing charm configuration options.
        relations: Static settings sent to related applications, keyed by endpoint name.
        env: Workload environment variables rendered from templates over relation data,
            charm configuration and application settings. ``None`` removes a variable.
    """

    prometheus: PrometheusConfig | None = Field(
        default=None, description="Prometheus configuration"
    )
    config: ConfigOptions = Field(default_factory=ConfigOptions)
    relations: dict[str, OAuthRelationConfig] = Field(
        default_factory=dict,
        description="Static settings sent to related applications, keyed by endpoint name.",
    )
    env: dict[str, str | None] = Field(
        default_factory=dict,
        description="Workload environment variables rendered from '${namespace.field}' templates.",
    )
    framework_logging_format: LoggingFormat = Field(
        default=LoggingFormat.NONE,
        description="Structured logging format for the framework server (e.g. 'json').",
    )

    port: int = Field(
        default=8080,
        gt=0,
        le=65535,
        description="Port on which the application server listens.",
    )
    metrics_port: int = Field(
        default=8080,
        alias="metrics-port",
        gt=0,
        le=65535,
        description="Port on which the application serves metrics.",
    )
    metrics_path: str = Field(
        default="/metrics",
        alias="metrics-path",
        description="HTTP resource path on which the application serves metrics.",
    )

    @field_validator("framework_logging_format", mode="before")
    @classmethod
    def _coerce_none_to_logging_format_none(cls, v: object) -> object:
        """Coerce a missing/null YAML value to ``LoggingFormat.NONE``.

        Args:
            v: The raw field value from YAML (may be ``None`` when the key is
               absent or explicitly set to ``null``).

        Returns:
            ``LoggingFormat.NONE`` if *v* is ``None``, otherwise *v* unchanged.
        """
        return LoggingFormat.NONE if v is None else v

    @field_validator("env")
    @classmethod
    def _validate_env(cls, env: dict[str, str | None]) -> dict[str, str | None]:
        """Validate environment variable names and template syntax.

        Args:
            env: Environment variable names mapped to templates.

        Returns:
            The validated mapping.

        Raises:
            ValueError: If a name or template is invalid.
        """
        for name, template in env.items():
            if not name or "\0" in name or "=" in name:
                raise ValueError(
                    f"invalid environment variable name {name!r}: "
                    "names must be non-empty and contain neither '=' nor NUL"
                )
            if template is not None:
                try:
                    env_templates.parse(template)
                except ValueError as exc:
                    raise ValueError(f"{name}: {exc}") from exc
        return env

    def application_port(self, *, default_port: int) -> int:
        """Return the configured application port or the framework default.

        Args:
            default_port: Framework-specific application port.

        Returns:
            The configured application port when explicitly set, otherwise the framework default.
        """
        return self.port if "port" in self.model_fields_set else default_port

    def metrics_endpoint(self, *, default_port: int, default_path: str) -> tuple[int, str]:
        """Return the configured workload metrics endpoint or framework defaults.

        Args:
            default_port: Framework-specific metrics port.
            default_path: Framework-specific metrics path.

        Returns:
            The resolved metrics port and path.
        """
        port = self.metrics_port if "metrics_port" in self.model_fields_set else default_port
        path = self.metrics_path if "metrics_path" in self.model_fields_set else default_path
        return port, path

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def read_paas_config(charm_root: pathlib.Path | None = None) -> PaasConfig:
    """Read and validate the paas-config.yaml file.

    Args:
        charm_root: Path to the charm root directory. If None, uses current directory.

    Returns:
        PaasConfig object. Returns empty PaasConfig() if file doesn't exist or is empty.

    Raises:
        PaasConfigError: If the file exists but is invalid (malformed YAML
            or schema validation error).
    """
    if charm_root is None:
        charm_root = pathlib.Path.cwd()

    config_path = charm_root / CONFIG_FILE_NAME

    if not config_path.exists():
        logger.info("No %s file found, using default configuration", CONFIG_FILE_NAME)
        return PaasConfig()

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config_data = yaml.safe_load(config_file) or {}
    except yaml.YAMLError as exc:
        error_msg = f"Invalid YAML in {CONFIG_FILE_NAME}: {exc}"
        logger.error(error_msg)
        raise PaasConfigError(error_msg) from exc
    except (OSError, IOError) as exc:
        error_msg = f"Failed to read {CONFIG_FILE_NAME}: {exc}"
        logger.error(error_msg)
        raise PaasConfigError(error_msg) from exc

    try:
        return PaasConfig(**config_data)
    except ValidationError as exc:
        error_details = build_validation_error_message(exc)
        error_msg = f"Invalid {CONFIG_FILE_NAME}: {error_details.short}"
        logger.error("%s: %s", error_msg, error_details.long)
        raise PaasConfigError(error_msg) from exc
