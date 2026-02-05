# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for reading and validating the paas-config.yaml configuration file."""

import logging
import pathlib
import typing

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from paas_charm.exceptions import PaasConfigError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "paas-config.yaml"


class StaticConfig(BaseModel):
    """Prometheus static configuration for scrape targets.

    Attributes:
        targets: List of target hosts to scrape (e.g., ["*:8000", "localhost:9090"]).
        labels: Optional labels to assign to all metrics from these targets.
        model_config: Pydantic model configuration.
    """

    targets: typing.List[str] = Field(description="List of target hosts to scrape")
    labels: typing.Dict[str, str] | None = Field(
        default=None, description="Labels assigned to all metrics scraped from the targets"
    )

    model_config = ConfigDict(extra="forbid")


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
        default="/metrics", description="HTTP resource path on which to fetch metrics"
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
        """Validate that all job_names are unique."""
        if not self.scrape_configs:
            return self

        job_names = [sc.job_name for sc in self.scrape_configs]
        duplicates = [name for name in set(job_names) if job_names.count(name) > 1]

        if duplicates:
            raise ValueError(
                f"Duplicate job_name values found in prometheus.scrape_configs: "
                f"{', '.join(sorted(set(duplicates)))}. Each job must have a unique name."
            )

        return self


class PaasConfig(BaseModel):
    """Configuration from paas-config.yaml file.

    Attributes:
        prometheus: Prometheus-related configuration.
        model_config: Pydantic model configuration.
    """

    prometheus: PrometheusConfig | None = Field(
        default=None, description="Prometheus configuration"
    )

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
