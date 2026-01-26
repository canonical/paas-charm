# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for go charm integration tests."""

import os
import pathlib

import jubilant
import pytest

from tests.integration.conftest import build_charm_file
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/go/charm")


@pytest.fixture(scope="module", name="go_app")
def go_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    go_app_image: str,
    tmp_path_factory,
):
    """Build and deploy the go charm."""
    app_name = "go-k8s"

    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return App(app_name)

    # Deploy postgresql if not already deployed
    if not juju.status().apps.get("postgresql-k8s"):
        juju.deploy(
            "postgresql-k8s",
            channel="14/edge",
            base="ubuntu@22.04",
            trust=True,
            config={
                "profile": "testing",
                "plugin_hstore_enable": "true",
                "plugin_pg_trgm_enable": "true",
            },
        )

    resources = {
        "app-image": go_app_image,
    }
    charm_file = build_charm_file(pytestconfig, "go", tmp_path_factory)

    try:
        juju.deploy(
            charm=charm_file,
            app=app_name,
            resources=resources,
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    # Add required relations
    try:
        juju.integrate(app_name, "postgresql-k8s:database")
    except jubilant.CLIError as err:
        if "already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: jubilant.all_active(status, app_name, "postgresql-k8s"), timeout=600)
    return App(app_name)


@pytest.fixture(scope="module", name="traefik_app")
def deploy_traefik_fixture(
    juju: jubilant.Juju,
    traefik_app_name: str,
    external_hostname: str,
):
    """Deploy traefik."""
    if not juju.status().apps.get(traefik_app_name):
        juju.deploy(
            "traefik-k8s",
            app=traefik_app_name,
            channel="edge",
            trust=True,
            config={
                "external_hostname": external_hostname,
                "routing_mode": "subdomain",
            },
        )
    juju.wait(
        lambda status: status.apps[traefik_app_name].is_active,
        error=jubilant.any_blocked,
    )
    return App(traefik_app_name)
