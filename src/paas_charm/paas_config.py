# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for reading and validating the paas-config.yaml configuration file."""

import logging
import pathlib
import typing

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from paas_charm.exceptions import CharmConfigInvalidError
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


def read_paas_config(charm_root: pathlib.Path | None = None) -> PaasConfig | None:
    """Read and validate the paas-config.yaml file.

    Args:
        charm_root: Path to the charm root directory. If None, uses current directory.

    Returns:
        PaasConfig object if file exists and is valid, None if file doesn't exist.

    Raises:
        CharmConfigInvalidError: If the file exists but is invalid (malformed YAML
            or schema validation error).
    """
    if charm_root is None:
        charm_root = pathlib.Path.cwd()

    config_path = charm_root / CONFIG_FILE_NAME

    if not config_path.exists():
        logger.info("No %s file found, using default configuration", CONFIG_FILE_NAME)
        return None

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config_data = yaml.safe_load(config_file)
    except yaml.YAMLError as exc:
        error_msg = f"Invalid YAML in {CONFIG_FILE_NAME}: {exc}"
        logger.error(error_msg)
        raise CharmConfigInvalidError(error_msg) from exc
    except (OSError, IOError) as exc:
        error_msg = f"Failed to read {CONFIG_FILE_NAME}: {exc}"
        logger.error(error_msg)
        raise CharmConfigInvalidError(error_msg) from exc

    if config_data is None:
        logger.warning("%s file is empty, using default configuration", CONFIG_FILE_NAME)
        return None

    try:
        return PaasConfig(**config_data)
    except ValidationError as exc:
        error_details = build_validation_error_message(exc, underscore_to_dash=True)
        error_msg = f"Invalid {CONFIG_FILE_NAME}: {error_details.short}"
        logger.error("%s: %s", error_msg, error_details.long)
        raise CharmConfigInvalidError(error_msg) from exc
