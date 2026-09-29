# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Framework related base classes."""

import typing

import pydantic


class FrameworkConfig(pydantic.BaseModel):
    """Base class for framework config models."""

    @pydantic.model_validator(mode="before")
    @classmethod
    def resolve_secret_key(cls, data: dict[str, str | int | bool | dict[str, str] | None]) -> dict:
        """Read the secret content of the *-secret-key configuration.

        Args:
            data: model input.

        Returns:
            modified input with the *-secret-key secret content replaced by its plaintext value.

        Raises:
            ValueError: if the *-secret-key secret content is invalid.
            NotImplementedError: ill-formed subclasses.
        """
        # Bandit thinks the following are secrets which they are not
        secret_key_field = "secret_key"  # nosec B105
        # Mypy thinks model_fields does not have get attribute
        if not cls.model_fields.get(secret_key_field, None):  # type: ignore
            secret_key_field = "app_secret_key"  # nosec B105
        # Mypy thinks model_fields does not have get attribute
        secret_key_config_name = cls.model_fields.get(secret_key_field).alias  # type: ignore
        if not secret_key_config_name:
            raise NotImplementedError("framework configuration secret_key field has no alias")
        if isinstance(data.get(secret_key_config_name), dict):
            secret_value = typing.cast(dict[str, str], data[secret_key_config_name])
            if "value" not in secret_value:
                raise ValueError(
                    f"{secret_key_config_name} missing 'value' key in the secret content"
                )
            if len(secret_value) > 1:
                raise ValueError(f"{secret_key_config_name} secret contains multiple values")
            data[secret_key_config_name] = secret_value["value"]
        return data
