# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Collect charm template schemas, runtime namespaces, and apply env templates."""

import logging
from collections.abc import Collection, Mapping
from dataclasses import asdict, fields
from typing import Any

from charmlibs.interfaces.openfga import OpenfgaProviderAppData
from charmlibs.interfaces.smtp import SmtpRelationData
from charms.squid_forward_proxy.v0.http_proxy import ProxyConfig
from dpcharmlibs.interfaces import ValkeyResponseModel
from ops import RelationMeta

from paas_charm import env_templates
from paas_charm.charm_state import CharmState
from paas_charm.databases import PaaSDatabaseRelationData
from paas_charm.exceptions import PaasConfigError
from paas_charm.oauth import PaaSOAuthRelationData
from paas_charm.paas_config import OAuthRelationConfig
from paas_charm.rabbitmq import PaaSRabbitMQRelationData
from paas_charm.relation_fields import (
    DatabaseURLFields,
    RabbitURLFields,
    database_fields,
    rabbit_fields,
)
from paas_charm.relations import CustomRelation
from paas_charm.s3 import PaaSS3RelationData, S3Relation
from paas_charm.saml import PaaSSAMLRelationData, SamlRelation
from paas_charm.smtp import SmtpRelation
from paas_charm.tracing import PaaSTracingRelationData
from paas_charm.utils import get_endpoints_by_interface_name
from paas_charm.valkey import ValkeyRelation

logger = logging.getLogger(__name__)


def template_endpoints(  # pylint: disable=too-many-arguments
    *,
    requires: Mapping[str, RelationMeta],
    peers: Mapping[str, RelationMeta],
    has_rabbitmq: bool,
    has_tracing: bool,
    has_openfga: bool,
    has_http_proxy: bool,
    has_oauth: bool,
    database_endpoints: Collection[str],
    builtin_relations: Collection[CustomRelation],
) -> dict[str, set[str]]:
    """Describe endpoint fields independently of whether a provider is related.

    Args:
        requires: Declared requires relations from charm metadata.
        peers: Declared peer relations from charm metadata.
        has_rabbitmq: Whether the built-in RabbitMQ requirer is bound.
        has_tracing: Whether the built-in tracing requirer is bound.
        has_openfga: Whether the built-in OpenFGA requirer is bound.
        has_http_proxy: Whether the built-in http-proxy requirer is bound.
        has_oauth: Whether the built-in OAuth requirer is bound.
        database_endpoints: Bound built-in database endpoint names.
        builtin_relations: Active built-in wrapper relations eligible for templates.

    Returns:
        Declared endpoints mapped to their built-in template fields.
    """
    db_fields = {f.name for f in fields(DatabaseURLFields)}
    result: dict[str, set[str]] = {name: set() for name in requires}
    if has_rabbitmq:
        result["rabbitmq"] = set(PaaSRabbitMQRelationData.model_fields) | {
            f.name for f in fields(RabbitURLFields)
        }
    if has_tracing:
        result["tracing"] = set(PaaSTracingRelationData.model_fields)
    if has_openfga:
        result["openfga"] = set(OpenfgaProviderAppData.model_fields)
    if has_http_proxy:
        result["http-proxy"] = {f.name for f in fields(ProxyConfig)}
    if "ingress" in requires and requires["ingress"].interface_name == "ingress":
        result["ingress"] = {"url"}
    if "peers" in peers:
        result["peers"] = {"fqdns"}
    for name in database_endpoints:
        result[name] = set(PaaSDatabaseRelationData.model_fields) | db_fields
    if has_oauth:
        ((endpoint, _),) = get_endpoints_by_interface_name(dict(requires), "oauth")
        result[endpoint] = set(PaaSOAuthRelationData.model_fields) | {"redirect_path"}
    wrappers = {
        ValkeyRelation: set(ValkeyResponseModel.model_fields) | db_fields,
        S3Relation: set(PaaSS3RelationData.model_fields),
        SamlRelation: set(PaaSSAMLRelationData.model_fields),
        SmtpRelation: set(SmtpRelationData.model_fields),
    }
    for relation in builtin_relations:
        result[relation.relation_name] = next(
            (names for cls, names in wrappers.items() if isinstance(relation, cls)),
            set(),
        )
    return result


def apply_env_templates(env: dict[str, str], charm_state: CharmState, port: int) -> None:
    """Render the ``env`` templates from paas-config.yaml into the environment.

    Templates override any other variable. Variables whose templates reference values
    that are unavailable are omitted.

    Args:
        env: The environment to update in place.
        charm_state: The charm state carrying templates, config, and integration data.
        port: The workload listening port.

    Raises:
        PaasConfigError: If a rendered value contains a NUL character.
    """
    if not charm_state.env_templates:
        return
    namespaces = _template_namespaces(charm_state, port)
    for name, template in charm_state.env_templates.items():
        value, unresolved = env_templates.render(template, namespaces)
        if value is None:
            logger.info(
                "Environment variable %r is not set: unresolved references %s",
                name,
                ", ".join(unresolved),
            )
            continue
        if "\0" in value:
            raise PaasConfigError(f"paas-config.yaml: env.{name}: rendered value contains NUL")
        if name in env:
            logger.debug("env template overwrites environment variable %r", name)
        env[name] = value


def _template_namespaces(charm_state: CharmState, port: int) -> dict[str, Any]:
    """Collect the values available to ``env`` templates.

    Args:
        charm_state: The charm state carrying config and integration data.
        port: The workload listening port.

    Returns:
        Field values keyed by namespace and field name.
    """
    return {
        "relations": _relation_template_fields(charm_state),
        "app": env_templates.model_fields(
            env_templates.AppFields(
                name=charm_state.app_name or None,
                base_url=charm_state.base_url or None,
                port=port,
            )
        ),
        "config": env_templates.config_fields(charm_state.charm_config),
    }


def _relation_template_fields(charm_state: CharmState) -> dict[str, dict[str, str]]:
    """Collect built-in relation fields available to ``env`` templates.

    Args:
        charm_state: The charm state carrying integration data.

    Returns:
        Relation field values keyed by endpoint name.
    """
    integrations = charm_state.integrations
    relations: dict[str, dict[str, str]] = {
        endpoint: {**env_templates.model_fields(db_data), **database_fields(db_data.uris)}
        for endpoint, db_data in integrations.databases_relation_data.items()
    }
    if integrations.rabbitmq:
        relations["rabbitmq"] = {
            **env_templates.model_fields(integrations.rabbitmq),
            **rabbit_fields(integrations.rabbitmq),
        }
    for endpoint, model in (
        ("tracing", integrations.tracing),
        ("openfga", integrations.openfga),
    ):
        if model:
            relations[endpoint] = env_templates.model_fields(model)
    if proxy := integrations.http_proxy:
        relations["http-proxy"] = asdict(proxy)
    for endpoint, key, value in (
        ("ingress", "url", integrations.ingress_url),
        ("peers", "fqdns", charm_state.peer_fqdns),
    ):
        if value:
            relations[endpoint] = {key: value}
    if integrations.oauth:
        oauth_config = charm_state.oauth_config or OAuthRelationConfig()
        relations[integrations.oauth.provider_name] = {
            **env_templates.model_fields(integrations.oauth),
            "redirect_path": oauth_config.redirect_path,
        }
    for relation in charm_state.template_relations:
        if isinstance(relation, (S3Relation, SamlRelation, SmtpRelation, ValkeyRelation)):
            relations[relation.relation_name] = relation.template_fields()
    return relations
