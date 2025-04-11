# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import os
import pathlib

import pytest
import pytest_asyncio
from juju.model import Model

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/expressjs")


@pytest_asyncio.fixture(scope="module", name="traefik_app")
async def deploy_traefik_fixture(
    model: Model,
    expressjs_app,  # pylint: disable=unused-argument
    traefik_app_name: str,
    external_hostname: str,
):
    """Deploy traefik."""
    app = await model.deploy(
        "traefik-k8s",
        application_name=traefik_app_name,
        channel="edge",
        trust=True,
        config={
            "external_hostname": external_hostname,
            "routing_mode": "subdomain",
        },
    )
    await model.wait_for_idle(raise_on_blocked=True)

    return app


@pytest_asyncio.fixture(scope="module", name="loki_app")
async def deploy_loki_fixture(
    model: Model,
    loki_app_name: str,
):
    """Deploy loki."""
    app = await model.deploy(
        "loki-k8s", application_name=loki_app_name, channel="latest/stable", trust=True
    )
    await model.wait_for_idle(raise_on_blocked=True)

    return app


@pytest_asyncio.fixture(scope="module", name="cos_apps")
async def deploy_cos_fixture(
    model: Model,
    loki_app,  # pylint: disable=unused-argument
    prometheus_app,  # pylint: disable=unused-argument
    grafana_app_name: str,
):
    """Deploy the cos applications."""
    cos_apps = await model.deploy(
        "grafana-k8s",
        application_name=grafana_app_name,
        channel="1.0/stable",
        revision=82,
        series="focal",
        trust=True,
    )
    await model.wait_for_idle(status="active")
    return cos_apps
