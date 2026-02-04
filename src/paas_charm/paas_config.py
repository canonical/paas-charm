# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module for reading and validating the paas-config.yaml configuration file."""

import logging
import pathlib
import typing

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.utils import build_validation_error_message

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "paas-config.yaml"


class PaasConfig(BaseModel):
    """Configuration from paas-config.yaml file.

    Attributes:
        version: Configuration file schema version.
        prometheus: Prometheus-related configuration (reserved for future use).
        http_proxy: HTTP proxy configuration (reserved for future use).
    """

    version: str = Field(description="Configuration file schema version")
    prometheus: typing.Dict[str, typing.Any] | None = Field(
        default=None, description="Prometheus configuration (reserved for future use)"
    )
    http_proxy: typing.Dict[str, typing.Any] | None = Field(
        default=None,
        alias="http-proxy",
        description="HTTP proxy configuration (reserved for future use)",
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        """Validate the version field.

        Args:
            value: The version string to validate.

        Returns:
            The validated version string.

        Raises:
            ValueError: If the version is not supported.
        """
        supported_versions = {"1"}
        if value not in supported_versions:
            raise ValueError(
                f"Unsupported paas-config.yaml version: {value}. "
                f"Supported versions: {', '.join(sorted(supported_versions))}"
            )
        return value


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
