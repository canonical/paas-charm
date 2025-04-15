# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""
import logging
import pathlib
import subprocess  # nosec B404
from collections.abc import Generator
from typing import Any, Dict, cast

import jubilant
import pytest
from pytest_operator.plugin import OpsTest

from tests.integration.types import App

logger = logging.getLogger(__name__)

import os

import pytest_asyncio
from juju.model import Model

from tests.integration.helpers import inject_venv

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

import pathlib


@pytest.fixture(scope="session")
def app_config():
    """Provides app config."""
    yield {}

@pytest.fixture(scope="session")
def charm_file(metadata: Dict[str, Any], pytestconfig: pytest.Config):
    """Pytest fixture that packs the charm and returns the filename, or --charm-file if set."""
    charm_file = pytestconfig.getoption("--charm-file")
    if charm_file:
        yield charm_file
        return

    try:
        subprocess.run(
            ["charmcraft", "pack"], check=True, capture_output=True, text=True
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    app_name = metadata["name"]
    charm_path = pathlib.Path(__file__).parent.parent.parent
    charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name} .charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    yield str(charms[0])

@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    def show_debug_log(juju: jubilant.Juju):
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return


def build_charm_file(
    pytestconfig: pytest.Config, ops_test: OpsTest, tmp_path_factory, framework
) -> str:
    """Get the existing charm file if exists, build a new one if not."""
    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if f"/{framework}-k8s" in f), None
    )

    if not charm_file:
        charm_location = PROJECT_ROOT / f"examples/{framework}/charm"
        if framework == "flask":
            charm_location = PROJECT_ROOT / f"examples/{framework}"
        try:
            subprocess.run(
                ["charmcraft", "pack", "--project-dir", charm_location], check=True, capture_output=True, text=True
            )  # nosec B603, B607

            app_name = "expressjs-k8s"
            charm_path = pathlib.Path(__file__).parent.parent.parent.parent
            charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
            assert charms, f"{app_name} .charm file not found"
            assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
            charm_file = str(charms[0])
        except subprocess.CalledProcessError as exc:
            raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    return pathlib.Path(charm_file).absolute()


@pytest.fixture(scope="module", name="app")
def app_fixture(
    juju: jubilant.Juju,
    app_config: Dict[str, str],
    pytestconfig: pytest.Config,
    ops_test: OpsTest,
    tmp_path_factory,
):
    # pylint: disable=too-many-locals
    """Discourse charm used for integration testing.
    Builds the charm and deploys it and the relations it depends on.
    """
    app_name = "expressjs-k8s"

    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield App(app_name)
        return

    juju.deploy(
        "postgresql-k8s",
        channel="14/stable",
        base="ubuntu@22.04",
        revision=300,
        trust=True,
        config={"profile": "testing"},
    )
    juju.wait(
        lambda status: jubilant.all_active(status, ["postgresql-k8s"]),
        timeout=20 * 60,
    )

    resources = {
        "app-image": pytestconfig.getoption("--expressjs-app-image"),
    }
    charm_file = build_charm_file(pytestconfig, ops_test, tmp_path_factory, "expressjs")
    juju.deploy(
        charm=charm_file,
        resources=resources,
    )

    juju.wait(lambda status: jubilant.all_waiting(status, [app_name]))

    # configure postgres
    juju.config(
        "postgresql-k8s",
        {
            "plugin_hstore_enable": "true",
            "plugin_pg_trgm_enable": "true",
        },
    )
    juju.wait(lambda status: jubilant.all_active(status, ["postgresql-k8s"]))

    # Add required relations
    status = juju.status()
    assert status.apps[app_name].units[app_name + "/0"].is_waiting
    juju.integrate(app_name, "postgresql-k8s:database")
    juju.wait(jubilant.all_active)

    yield App(app_name)

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
