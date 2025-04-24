# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for ExpressJS charm integration tests."""
import logging
import pathlib

import jubilant
import pytest

from tests.integration.conftest import build_charm_file
from tests.integration.types import App

logger = logging.getLogger(__name__)


PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.mark.skip_juju_version("3.4")
@pytest.fixture(scope="module", name="expressjs_app")
def expressjs_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
):
    """ExpressJS charm used for integration testing.
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
    charm_file = build_charm_file(pytestconfig, "expressjs")
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
