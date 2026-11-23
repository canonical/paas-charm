# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Render the ``env`` section of paas-config.yaml.

Each value is a template where ``${<namespace>.<field>}`` is replaced with a value from the
charm, for example ``${postgresql.hostname}`` or ``${app.base_url}``. ``${<ref>:-<default>}``
uses ``<default>`` when the reference has no value, and ``$$`` produces a literal ``$``.
"""

import enum
import json
import re
import typing
from dataclasses import dataclass

from pydantic import BaseModel, SecretStr
from pydantic_core import to_jsonable_python

from paas_charm.exceptions import PaasConfigError

# ``$$``, ``${...}`` or any other ``$``, which is rejected.
_TOKEN = re.compile(r"\$(?:(\$)|\{([^}]*)\}|)")
_REFERENCE = re.compile(r"^(?P<namespace>[A-Za-z0-9_-]+)\.(?P<field>[A-Za-z0-9_.-]+)$")

APP_NAMESPACE = "app"
CONFIG_NAMESPACE = "config"
APP_FIELDS = frozenset({"name", "base_url", "port"})


@dataclass(frozen=True)
class Reference:
    """A ``${...}`` reference in a template.

    Attrs:
        namespace: The endpoint name, ``app`` or ``config``.
        field: The field in the namespace, which may contain dots.
        default: The value used when the reference is unresolved, if any.
    """

    namespace: str
    field: str
    default: str | None


def parse(template: str) -> list[str | Reference]:
    """Split a template into literal text and references.

    Args:
        template: The template to parse.

    Returns:
        Literal strings and references, in order.

    Raises:
        ValueError: If the template is malformed.
    """
    parts: list[str | Reference] = []
    position = 0
    for match in _TOKEN.finditer(template):
        start = match.start()
        parts.append(template[position:start])
        position = match.end()
        if match.group(1):
            parts.append("$")
            continue
        expression = match.group(2)
        if expression is None:
            raise ValueError(
                f"unexpected '$' at position {match.start()}: "
                "use '${<namespace>.<field>}' for a reference or '$$' for a literal '$'"
            )
        reference, separator, default = expression.partition(":-")
        reference_match = _REFERENCE.match(reference)
        if not reference_match:
            raise ValueError(
                f"invalid reference '${{{expression}}}': expected '${{<namespace>.<field>}}'"
            )
        parts.append(
            Reference(
                namespace=reference_match.group("namespace"),
                field=reference_match.group("field"),
                default=default if separator else None,
            )
        )
    parts.append(template[position:])
    return [part for part in parts if part != ""]


def references(template: str) -> list[Reference]:
    """Return the references in a template.

    Args:
        template: The template to inspect.

    Returns:
        The references in the template.
    """
    return [part for part in parse(template) if isinstance(part, Reference)]


def render(
    template: str, namespaces: typing.Mapping[str, typing.Mapping[str, str]]
) -> tuple[str | None, list[Reference]]:
    """Render a template.

    Args:
        template: The template to render.
        namespaces: Field values keyed by namespace and field name.

    Returns:
        The rendered value, or None if a reference without a default is unresolved, and the
        unresolved references.
    """
    rendered: list[str] = []
    unresolved: list[Reference] = []
    for part in parse(template):
        if isinstance(part, str):
            rendered.append(part)
            continue
        value = namespaces.get(part.namespace, {}).get(part.field)
        if value is None:
            if part.default is None:
                unresolved.append(part)
                continue
            value = part.default
        rendered.append(value)
    return (None if unresolved else "".join(rendered)), unresolved


def to_template_value(value: typing.Any) -> str | None:
    """Convert a value to the string used in templates.

    Args:
        value: The value to convert.

    Returns:
        The string value, or None when the value is None.
    """
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    elif isinstance(value, enum.Enum):
        value = value.value
    elif isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, set, dict)):
        return json.dumps(to_jsonable_python(value))
    return str(value)


def model_fields(model: BaseModel | None) -> dict[str, str]:
    """Return the fields of a relation data model as template values.

    Args:
        model: The relation data model.

    Returns:
        Field names mapped to their template values, without fields that have no value.
    """
    if model is None:
        return {}
    return {
        name: value
        for name in type(model).model_fields
        if (value := to_template_value(getattr(model, name))) is not None
    }


def config_fields(config: typing.Mapping[str, typing.Any]) -> dict[str, str]:
    """Return charm configuration values as template values.

    Secret options resolve to a mapping, whose keys are exposed as ``<option>.<key>``.

    Args:
        config: Charm configuration with secrets resolved.

    Returns:
        Option names mapped to their template values.
    """
    fields: dict[str, str] = {}
    for option, value in config.items():
        if isinstance(value, dict):
            for key, content in value.items():
                if (converted := to_template_value(content)) is not None:
                    fields[f"{option}.{key}"] = converted
        elif (converted := to_template_value(value)) is not None:
            fields[option] = converted
    return fields


def env_fields(env: typing.Mapping[str, str], *prefixes: str) -> dict[str, str]:
    """Derive template fields from default environment variables.

    Args:
        env: Default environment variables of a relation.
        prefixes: Prefixes to strip, the first match is used.

    Returns:
        Lower-cased variable names without the prefix mapped to their values.
    """
    fields = {}
    for name, value in env.items():
        for prefix in prefixes:
            if name.startswith(prefix):
                fields[name.removeprefix(prefix).lower()] = value
                break
    return fields


def validate_env_templates(
    env: typing.Mapping[str, str | None],
    *,
    endpoints: typing.Collection[str],
    config_options: typing.Mapping[str, typing.Mapping[str, typing.Any]],
) -> None:
    """Validate that template references point to known namespaces and fields.

    Relation fields are only known at runtime, so only their endpoint name is validated.

    Args:
        env: Environment variable names mapped to templates.
        endpoints: Endpoint names declared under ``requires``.
        config_options: Charm configuration option metadata.

    Raises:
        PaasConfigError: If a reference is invalid.
    """
    for name, template in env.items():
        if template is None:
            continue
        for reference in references(template):
            error = _reference_error(reference, endpoints, config_options)
            if error:
                raise PaasConfigError(f"paas-config.yaml: env.{name}: {error}")


def _reference_error(
    reference: Reference,
    endpoints: typing.Collection[str],
    config_options: typing.Mapping[str, typing.Mapping[str, typing.Any]],
) -> str | None:
    """Return why a reference is invalid.

    Args:
        reference: The reference to check.
        endpoints: Endpoint names declared under ``requires``.
        config_options: Charm configuration option metadata.

    Returns:
        The reason the reference is invalid, or None if it is valid.
    """
    text = f"${{{reference.namespace}.{reference.field}}}"
    if reference.namespace not in (APP_NAMESPACE, CONFIG_NAMESPACE):
        if reference.namespace in endpoints:
            return None
        return (
            f"{text} references unknown namespace {reference.namespace!r}; expected a relation "
            f"endpoint, {APP_NAMESPACE!r} or {CONFIG_NAMESPACE!r}"
        )
    if reference.namespace in endpoints:
        return (
            f"{text} is ambiguous: {reference.namespace!r} is both a built-in namespace "
            "and a relation endpoint name"
        )
    if reference.namespace == APP_NAMESPACE:
        if reference.field in APP_FIELDS:
            return None
        return f"{text} references unknown field; expected one of {sorted(APP_FIELDS)}"
    return _config_reference_error(text, reference.field, config_options)


def _config_reference_error(
    text: str, field: str, config_options: typing.Mapping[str, typing.Mapping[str, typing.Any]]
) -> str | None:
    """Return why a ``config`` reference is invalid.

    Args:
        text: The reference as written in the template.
        field: The referenced field.
        config_options: Charm configuration option metadata.

    Returns:
        The reason the reference is invalid, or None if it is valid.
    """
    option, _, key = field.partition(".")
    if option not in config_options:
        return f"{text} references unknown charm configuration option {option!r}"
    is_secret = config_options[option].get("type") == "secret"
    if is_secret and not key:
        return f"{text} must reference a secret content key: '${{config.{option}.<key>}}'"
    if not is_secret and key:
        return f"{text} references a key of option {option!r}, which isn't a secret"
    return None
