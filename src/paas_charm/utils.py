# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Generic utility functions."""

import functools
import itertools
import os
import pathlib
import shutil
import typing

import ops
import yaml
from ops import RelationMeta
from pydantic import ValidationError

from paas_charm.exceptions import InvalidCustomCOSDirectoryError


class ValidationErrorMessage(typing.NamedTuple):
    """Class carrying status message and error log for pydantic validation errors.

    Attrs:
        short: Short error message to show in status message.
        long: Detailed error message for logging.
    """

    short: str
    long: str


def build_validation_error_message(
    exc: ValidationError, prefix: str | None = None, underscore_to_dash: bool = False
) -> ValidationErrorMessage:
    """Build a ValidationErrorMessage for error logging.

    Args:
        exc: ValidationError exception instance.
        prefix: Prefix to append to the error field names.
        underscore_to_dash: Replace underscores to dashes in the error field names.

    Returns:
        The ValidationErrorMessage for error logging..
    """
    fields = set(
        (
            (
                f'{prefix if prefix else ""}{".".join(str(loc) for loc in error["loc"])}'
                if error["loc"]
                else ""
            ),
            error["msg"],
        )
        for error in exc.errors()
    )

    if underscore_to_dash:
        fields = {(key.replace("_", "-"), value) for key, value in fields}

    missing_fields = {}
    invalid_fields = {}

    for loc, msg in fields:
        if "required" in msg.lower():
            missing_fields[loc] = msg
        else:
            invalid_fields[loc] = msg

    short_str_missing = f"missing options: {', '.join(missing_fields)}" if missing_fields else ""
    short_str_invalid = f"invalid options: {', '.join(invalid_fields)}" if invalid_fields else ""
    short_str = f"{short_str_missing}\
        {', ' if missing_fields and invalid_fields else ''}{short_str_invalid}"

    long_str_lines = "\n".join(
        f"- {key}: {value}"
        for key, value in itertools.chain(missing_fields.items(), invalid_fields.items())
    )
    long_str = f"invalid configuration:\n{long_str_lines}"

    return ValidationErrorMessage(short=short_str, long=long_str)


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
def config_metadata(charm_dir: pathlib.Path) -> dict:
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
    metadata = config_metadata(pathlib.Path(os.getcwd()))
    config_type = metadata["options"][key]["type"]
    if config_type != "secret":
        return charm.config.get(key)
    secret_id = charm.config.get(key)
    if secret_id is None:
        return None
    return charm.model.get_secret(id=typing.cast(str, secret_id))


def get_endpoints_by_interface_name(
    requires: dict[str, RelationMeta], interface_name: str
) -> list[tuple[str, RelationMeta]]:
    """Get the endpoints for a given interface name.

    Args:
        requires: relation requires dictionary from metadata
        interface_name: the interface name to filter endpoints

    Returns:
        A list of endpoints that match the given interface name.
    """
    return [
        (endpoint_name, endpoint)
        for endpoint_name, endpoint in requires.items()
        if endpoint.interface_name == interface_name
    ]


def build_k8s_unit_fqdn(app_name: str, unit_identifier: str, model_name: str) -> str:
    """Build Kubernetes FQDN for a unit using service discovery.

    Args:
        app_name: Application name (e.g., "flask-app").
        unit_identifier: Unit identifier - can be unit number ("0"), unit name with slash
            ("flask-app/0"), or unit name with dash ("flask-app-0").
        model_name: Juju model name.

    Returns:
        Full Kubernetes FQDN for the unit.

    Example:
        >>> build_k8s_unit_fqdn("flask-app", "0", "my-model")
        "flask-app-0.flask-app-endpoints.my-model.svc.cluster.local"
        >>> build_k8s_unit_fqdn("flask-app", "flask-app/0", "my-model")
        "flask-app-0.flask-app-endpoints.my-model.svc.cluster.local"
    """
    if "/" in unit_identifier:
        normalized = unit_identifier.replace("/", "-")
    elif not unit_identifier.startswith(app_name):
        normalized = f"{app_name}-{unit_identifier}"
    else:
        normalized = unit_identifier

    return f"{normalized}.{app_name}-endpoints.{model_name}.svc.cluster.local"


def merge_cos_directories(
    default_dir: pathlib.Path, custom_dir: pathlib.Path, merged_dir: pathlib.Path
) -> None:
    """Merge the default COS directory with the custom COS directory.

    Files in the custom COS directory will have `custom_` prefix to avoid conflicts with default COS files.

    Args:
        default_dir: the default COS directory.
        custom_dir: the custom COS directory.
        merged_dir: the output merged COS directory.
    """

    if merged_dir.is_dir():
        shutil.rmtree(merged_dir)

    shutil.copytree(default_dir, merged_dir)

    validate_cos_custom_dir(custom_dir)

    if custom_dir.is_dir():
        for subdir in custom_dir.iterdir():
            for file in subdir.iterdir():
                if file.is_file():
                    shutil.copy(file, merged_dir / subdir.name / f"custom_{file.name}")


def validate_cos_custom_dir(custom_dir: pathlib.Path) -> None:
    """Validate the custom COS directory.

    Args:
        custom_dir: the custom COS directory.

    Raises:
        InvalidCustomCOSDirectoryError: if the custom COS directory is invalid.
    """

    COS_SUBDIRS = {"grafana_dashboards", "loki_alert_rules", "prometheus_alert_rules"}

    if custom_dir.is_dir():
        for p in custom_dir.iterdir():
            if p.is_file():
                raise InvalidCustomCOSDirectoryError(
                    f"custom COS directory cannot contain a file named {p.name}"
                )
            elif p.is_dir():
                if p.name not in COS_SUBDIRS:
                    raise InvalidCustomCOSDirectoryError(
                        f"custom COS directory cannot contain a subdirectory named {p.name}"
                    )
