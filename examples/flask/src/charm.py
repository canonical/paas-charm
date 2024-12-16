#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm service."""

import logging
import typing

import ops
from charms.tempo_coordinator_k8s.v0.charm_tracing import trace_charm
from charms.tempo_coordinator_k8s.v0.tracing import TracingEndpointRequirer, charm_tracing_config

import paas_charm.flask

logger = logging.getLogger(__name__)

@trace_charm(tracing_endpoint="charm_tracing_endpoint")
class FlaskCharm(paas_charm.flask.Charm):
    """Flask Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)
        self.charm_tracing = TracingEndpointRequirer(self, relation_name="charm-tracing", protocols=["otlp_http"])
        self.workload_tracing = TracingEndpointRequirer(self, relation_name="workload-tracing", protocols=["otlp_grpc"])
        if self.charm_tracing.is_ready():
            logger.info("```````````````: %s", self.charm_tracing.get_endpoint("otlp_http"))
        if self.workload_tracing.is_ready():
            logger.info("```````````````: %s", self.workload_tracing.get_endpoint("otlp_grpc"))
        # self.charm_tracing_endpoint, _ = charm_tracing_config(self.charm_tracing,None)

    @property
    def charm_tracing_endpoint(self) -> str | None:
        """Tempo endpoint for workload tracing"""
        if self.charm_tracing.is_ready():
            return self.charm_tracing.get_endpoint("otlp_http")
        return None


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(FlaskCharm)
