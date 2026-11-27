# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Validate and render static Jinja lookups in the env section of paas-config.yaml."""

import enum
import json
import typing
from collections.abc import Collection, Mapping
from difflib import get_close_matches
from functools import lru_cache

from jinja2 import ChainableUndefined, Template, TemplateSyntaxError, nodes
from jinja2.sandbox import ImmutableSandboxedEnvironment
from pydantic import BaseModel, SecretStr
from pydantic_core import to_jsonable_python

from paas_charm.exceptions import PaasConfigError

Path = tuple[str, ...]
Context = Mapping[str, typing.Any]


class AppFields(BaseModel):
    """Application fields shared by template validation and rendering.

    Attrs:
        name: Juju application name.
        base_url: Public application URL.
        port: Workload port.
    """

    name: str | None
    base_url: str | None
    port: int


class _FieldEnvironment(ImmutableSandboxedEnvironment):
    """Resolve both dot and bracket notation as data keys inside Jinja's immutable sandbox."""

    def getitem(self, obj: typing.Any, argument: typing.Any) -> typing.Any:
        """Look up a data key, propagating missing values for the default filter.

        Args:
            obj: Parent mapping or missing parent.
            argument: Static key in the template.

        Returns:
            The field value or a Jinja undefined value.
        """
        if isinstance(obj, Mapping) and argument in obj and obj[argument] is not None:
            return obj[argument]
        return self.undefined(name=argument)

    def getattr(self, obj: typing.Any, attribute: str) -> typing.Any:
        """Resolve dot notation using the same keys as bracket notation.

        Args:
            obj: Parent mapping or missing parent.
            attribute: Requested field name.

        Returns:
            The field value or a Jinja undefined value.
        """
        return self.getitem(obj, attribute)


_ENV = _FieldEnvironment(
    undefined=ChainableUndefined, keep_trailing_newline=True, autoescape=False
)
_ENV.globals.clear()
_ENV.tests.clear()
_ENV.filters = {"default": _ENV.filters["default"]}


def _path(node: nodes.Expr) -> Path:
    """Extract a static data path from a Jinja expression.

    Args:
        node: Jinja expression to inspect.

    Returns:
        Path components from root to leaf.

    Raises:
        ValueError: If the expression is not a static lookup.
    """
    if isinstance(node, nodes.Name):
        return (node.name,)
    if isinstance(node, nodes.Getattr):
        return (*_path(node.node), node.attr)
    if isinstance(node, nodes.Getitem) and isinstance(node.arg, nodes.Const):
        if isinstance(node.arg.value, str):
            return (*_path(node.node), node.arg.value)
    raise ValueError("expected a static field lookup using dot notation or quoted keys")


def _reference(node: nodes.Expr) -> tuple[Path, bool]:
    """Read a field reference and whether it has a default.

    Args:
        node: Output expression.

    Returns:
        Static path and whether the value is required.

    Raises:
        ValueError: If the filter is unsupported.
    """
    if not isinstance(node, nodes.Filter):
        return _path(node), True
    if not (
        node.name == "default"
        and node.node is not None
        and len(node.args) == 1
        and isinstance(node.args[0], nodes.Const)
        and isinstance(node.args[0].value, str)
        and not (node.kwargs or node.dyn_args or node.dyn_kwargs)
    ):
        raise ValueError("expected default('literal string') after a field lookup")
    return _path(node.node), False


@lru_cache(maxsize=256)
def parse(source: str) -> tuple[Template, tuple[tuple[Path, bool], ...]]:
    """Compile a template and collect its references for validation and missing-value handling.

    Args:
        source: Jinja template text.

    Returns:
        Compiled template and its static references.

    Raises:
        ValueError: If the Jinja syntax or expression is unsupported.
    """
    try:
        tree = _ENV.parse(source)
    except TemplateSyntaxError as exc:
        raise ValueError(exc.message) from exc
    refs: list[tuple[Path, bool]] = []
    for output in tree.body:
        if not isinstance(output, nodes.Output):
            raise ValueError("only Jinja output expressions are supported")
        refs.extend(
            _reference(node) for node in output.nodes if not isinstance(node, nodes.TemplateData)
        )
    return _ENV.from_string(tree), tuple(refs)


def render(source: str, context: Context) -> tuple[str | None, list[str]]:
    """Render an assignment only if all references without defaults resolve.

    Args:
        source: Jinja template text.
        context: Nested mappings of available fields.

    Returns:
        Rendered text or the unresolved paths, never their values.
    """
    template, refs = parse(source)
    missing: list[str] = []
    for path, required in refs:
        if required:
            value: typing.Any = context
            for key in path:
                if not isinstance(value, Mapping) or key not in value or value[key] is None:
                    missing.append(".".join(path))
                    break
                value = value[key]
    return (None, list(dict.fromkeys(missing))) if missing else (template.render(context), [])


def to_template_value(value: typing.Any) -> str | None:
    """Convert a model field to its workload string representation.

    Args:
        value: Relation or config value.

    Returns:
        Plain text, JSON for collections, or None for an absent field.
    """
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    elif isinstance(value, enum.Enum):
        value = value.value
    elif isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (bool, list, tuple, set, dict)):
        return json.dumps(to_jsonable_python(value))
    return str(value)


def model_fields(model: BaseModel | None) -> dict[str, str]:
    """Return the available template fields of a relation data model.

    Args:
        model: Relation data.

    Returns:
        Field names and string values.
    """
    if model is None:
        return {}
    return {
        k: text
        for k in type(model).model_fields
        if (text := to_template_value(getattr(model, k))) is not None
    }


def config_fields(config: Context) -> dict[str, typing.Any]:
    """Expose secret content as a nested mapping and scalar config as text.

    Args:
        config: Charm config with resolved secrets.

    Returns:
        Config values keyed by their exact option names.
    """
    return {
        k: v if isinstance(v, dict) else to_template_value(v)
        for k, v in config.items()
        if v is not None
    }


def validate_env_templates(
    env: Mapping[str, str],
    *,
    endpoints: Mapping[str, Collection[str]],
    config_options: Context,
) -> None:
    """Validate references independently of current config values and relation presence.

    Args:
        env: Templates by destination variable.
        endpoints: Declared endpoint names and their built-in template fields.
        config_options: Juju configuration metadata.

    Raises:
        PaasConfigError: If a template references an invalid field.
    """
    for name, source in env.items():
        for path, _ in parse(source)[1]:
            error = _reference_error(path, endpoints, config_options)
            if error:
                raise PaasConfigError(f"paas-config.yaml: env.{name}: {'.'.join(path)}: {error}")


def _reference_error(
    path: Path, endpoints: Mapping[str, Collection[str]], config: Context
) -> str | None:
    """Check a path against the available namespaces.

    Args:
        path: Static reference components.
        endpoints: Declared endpoints and known fields.
        config: Charm config option metadata.

    Returns:
        A diagnostic or None for a valid path.
    """
    match path:
        case ("app", field):
            return None if field in set(AppFields.model_fields) else "unknown application field"
        case ("config", option, *keys):
            return _config_error(option, keys, config)
        case ("relations", endpoint, field) if endpoint in endpoints:
            fields = endpoints[endpoint]
            if field in fields:
                return None
            return (
                "unknown built-in relation field"
                if fields
                else "relation does not expose template fields"
            )
        case ("relations", _, _):
            return "unknown relation endpoint"
        case _:
            return "unknown namespace, endpoint, option or field"


def _config_error(option: str, keys: list[str], config: Context) -> str | None:
    """Check an exact option name and whether its type permits the requested lookup.

    Args:
        option: Referenced option name.
        keys: Remaining components of the lookup.
        config: Charm config option metadata.

    Returns:
        A diagnostic or None for a valid config reference.
    """
    if option not in config:
        message = f"unknown charm configuration option {option!r}"
        if matches := get_close_matches(option, config, n=1, cutoff=0.8):
            message += f". Did you mean {matches[0]!r}?"
        return message
    if config[option].get("type") == "secret":
        return None if len(keys) == 1 else f"secret option {option!r} requires one content key"
    return f"option {option!r} isn't a secret and cannot be indexed" if keys else None
