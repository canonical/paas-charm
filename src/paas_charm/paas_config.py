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

from paas_charm.exceptions import PaasConfigError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "paas-config.yaml"
APP_JOB_NAME = "app"


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
        min_length=1,
        pattern=r"^/",
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
        app_scrape_config: Reserved application scrape job, if configured.
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

        app_scrape_config = self.app_scrape_config
        if app_scrape_config:
            if not app_scrape_config.metrics_path.strip("/"):
                raise ValueError("The 'app' scrape job metrics path must identify an endpoint")
            if len(app_scrape_config.static_configs) != 1:
                raise ValueError("The 'app' scrape job must define exactly one static config")
            targets = app_scrape_config.static_configs[0].targets
            if len(targets) != 1 or not targets[0].startswith("*:"):
                raise ValueError("The 'app' scrape job must define exactly one '*:PORT' target")
            port = targets[0].removeprefix("*:")
            if not port.isdigit() or not 1 <= int(port) <= 65535:
                raise ValueError("The 'app' scrape job target must use a port between 1 and 65535")

        return self

    @property
    def app_scrape_config(self) -> ScrapeConfig | None:
        """Return the reserved application scrape job, if configured."""
        return next(
            (
                scrape_config
                for scrape_config in self.scrape_configs or []
                if scrape_config.job_name == APP_JOB_NAME
            ),
            None,
        )


class PaasConfig(BaseModel):
    """Configuration from paas-config.yaml file.

    Attributes:
        prometheus: Prometheus-related configuration.
        framework_logging_format: Structured logging format for the framework server.
            Defaults to ``LoggingFormat.NONE`` (framework default logging).
            ``LoggingFormat.JSON`` ("json") is supported for FastAPI, Flask, and Django.
        model_config: Pydantic model configuration.
        port: Optional override for the port on which the application server listens.
    """

    prometheus: PrometheusConfig | None = Field(
        default=None, description="Prometheus configuration"
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

    def application_port(self, *, default_port: int) -> int:
        """Return the configured application port or the framework default.

        Args:
            default_port: Framework-specific application port.

        Returns:
            The configured application port when explicitly set, otherwise the framework default.
        """
        return self.port if "port" in self.model_fields_set else default_port

    def metrics_endpoint(self, *, default_port: int, default_path: str) -> tuple[int, str]:
        """Return the configured application metrics endpoint or framework defaults.

        Args:
            default_port: Framework-specific metrics port.
            default_path: Framework-specific metrics path.

        Returns:
            The resolved metrics port and path.
        """
        # Pylint resolves Pydantic model fields as FieldInfo rather than their annotated type.
        prometheus_config = self.prometheus
        app_scrape_config = (
            prometheus_config.app_scrape_config  # pylint: disable=no-member
            if prometheus_config is not None
            else None
        )
        if not app_scrape_config:
            return default_port, default_path
        target = app_scrape_config.static_configs[0].targets[0]
        return int(target.removeprefix("*:")), app_scrape_config.metrics_path

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
        error_details = build_validation_error_message(exc, underscore_to_dash=True)
        error_msg = f"Invalid {CONFIG_FILE_NAME}: {error_details.short}"
        logger.error("%s: %s", error_msg, error_details.long)
        raise PaasConfigError(error_msg) from exc
