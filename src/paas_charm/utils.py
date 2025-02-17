# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Generic utility functions."""
import functools
import os
import pathlib
import typing

import ops
import yaml
from pydantic import ValidationError


def build_validation_error_message(
    exc: ValidationError, prefix: str | None = None, underscore_to_dash: bool = False
) -> tuple[str, str]:
    """Build a tuple of strings for error logging.

    The tuple consists of:
        0-  A list of error fields from a pydantic exception to print at charm status.
        1-  A detailed list of error fields from a pydantic exception with their error
             messages. Best fit for printing error logs.

    Args:
        exc: ValidationError exception instance.
        prefix: Prefix to append to the error field names.
        underscore_to_dash: Replace underscores to dashes in the error field names.

    Returns:
        The tuple of 2 strings first for charm status, second for logging.
    """
    error_fields_unique = set(
        {(error["loc"][0] if error["loc"] else "", error["msg"]) for error in exc.errors()}
    )
    error_fields = {str(error_field[0]) for error_field in error_fields_unique}

    if prefix:
        error_fields = {f"{prefix}{error_field}" for error_field in error_fields}
        error_fields_unique = {
            (f"{prefix}{error_field[0]}", error_field[1]) for error_field in error_fields_unique
        }
    if underscore_to_dash:
        error_fields = {error_field.replace("_", "-") for error_field in error_fields}
        error_fields_unique = {
            (error_field[0].replace("_", "-"), error_field[1])
            for error_field in error_fields_unique
        }

    error_field_str = ""
    missing_options_str = ""
    error_field_log_str = "Configuration invalid:"
    for err in error_fields_unique:
        if "Field required" in err[1]:
            missing_options_str += f"{err[0]}, "
        else:
            error_field_str += f"{err[0]}, "
        error_field_log_str += f"\n\t- {err[0]}: {err[1]}"

    message_str = ""
    if missing_options_str:
        message_str += f"missing options: {missing_options_str[:-2]} "
    if error_field_str:
        message_str += f"invalid options: {error_field_str[:-2]}"

    return (message_str, error_field_log_str)


def enable_pebble_log_forwarding() -> bool:
    """Check if the current environment allows to enable pebble log forwarding feature.

    Returns:
        True if the current environment allows to enable pebble log forwarding feature.
    """
    juju_version = ops.JujuVersion.from_environ()
    if (juju_version.major, juju_version.minor) < (3, 4):
        return False
    try:
        # disable "imported but unused" and "import outside toplevel" error
        # pylint: disable=import-outside-toplevel,unused-import
        import charms.loki_k8s.v1.loki_push_api  # noqa: F401

        return True
    except ImportError:
        return False


@functools.lru_cache
def _config_metadata(charm_dir: pathlib.Path) -> dict:
    """Get charm configuration metadata for the given charm directory.

    Args:
        charm_dir: Path to the charm directory.

    Returns:
        The charm configuration metadata.

    Raises:
            ValueError: if the charm_dir input is invalid.
    """
    config_file = charm_dir / "config.yaml"
    if config_file.exists():
        return yaml.safe_load(config_file.read_text())
    config_file = charm_dir / "charmcraft.yaml"
    if config_file.exists():
        return yaml.safe_load(config_file.read_text())["config"]
    raise ValueError("charm configuration metadata doesn't exist")


def config_get_with_secret(
    charm: ops.CharmBase, key: str
) -> str | int | bool | float | ops.Secret | None:
    """Get charm configuration values.

    This function differs from ``ops.CharmBase.config.get`` in that for secret-typed configuration
    options, it returns the secret object instead of the secret ID in the configuration
    value. In other instances, this function is equivalent to ops.CharmBase.config.get.

    Args:
        charm: The charm instance.
        key: The configuration option key.

    Returns:
        The configuration value.
    """
    metadata = _config_metadata(pathlib.Path(os.getcwd()))
    config_type = metadata["options"][key]["type"]
    if config_type != "secret":
        return charm.config.get(key)
    secret_id = charm.config.get(key)
    if secret_id is None:
        return None
    return charm.model.get_secret(id=typing.cast(str, secret_id))
