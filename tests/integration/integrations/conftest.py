# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import os
import pathlib

import nest_asyncio
import pytest
import pytest_asyncio
from juju.application import Application
from juju.model import Model
from minio import Minio
from ops import JujuVersion
from pytest import Config
from pytest_operator.plugin import OpsTest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
nest_asyncio.apply()


@pytest.fixture(autouse=True)
def skip_by_juju_version(request, model):
    """Skip the test if juju version is lower then the `skip_juju_version` marker value."""
    if request.node.get_closest_marker("skip_juju_version"):
        current_version = JujuVersion(
            f"{model.info.agent_version.major}.{model.info.agent_version.minor}.{model.info.agent_version.patch}"
        )
        min_version = JujuVersion(request.node.get_closest_marker("skip_juju_version").args[0])
        if current_version < min_version:
            pytest.skip("Juju version is too old")


def pytest_configure(config):
    """Add new marker."""
    config.addinivalue_line(
        "markers",
        "skip_juju_version(version): skip test if Juju version is lower than version",
    )


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/flask")


async def deploy_and_configure_minio(ops_test: OpsTest, get_unit_ips) -> None:
    """Deploy and set up minio and s3-integrator needed for s3-like storage backend in the HA charms."""
    config = {
        "access-key": "accesskey",
        "secret-key": "secretkey",
    }
    minio_app = await ops_test.model.deploy("minio", channel="edge", trust=True, config=config)
    await ops_test.model.wait_for_idle(
        apps=[minio_app.name], status="active", timeout=2000, idle_period=45
    )
    minio_addr = (await get_unit_ips(minio_app.name))[0]

    mc_client = Minio(
        f"{minio_addr}:9000",
        access_key="accesskey",
        secret_key="secretkey",
        secure=False,
    )

    # create tempo bucket
    found = mc_client.bucket_exists("tempo")
    if not found:
        mc_client.make_bucket("tempo")

    # configure s3-integrator
    s3_integrator_app: Application = ops_test.model.applications["s3-integrator"]
    s3_integrator_leader: Unit = s3_integrator_app.units[0]

    await s3_integrator_app.set_config(
        {
            "endpoint": f"minio-0.minio-endpoints.{ops_test.model.name}.svc.cluster.local:9000",
            "bucket": "tempo",
        }
    )

    action = await s3_integrator_leader.run_action("sync-s3-credentials", **config)
    action_result = await action.wait()
    assert action_result.status == "completed"


@pytest_asyncio.fixture(scope="module", name="tempo_app")
async def deploy_tempo_cluster(ops_test: OpsTest, get_unit_ips):
    """Deploys tempo in its HA version together with minio and s3-integrator."""
    tempo_app = "tempo"
    worker_app = "tempo-worker"
    tempo_worker_charm_url, worker_channel = "tempo-worker-k8s", "edge"
    tempo_coordinator_charm_url, coordinator_channel = "tempo-coordinator-k8s", "edge"
    await ops_test.model.deploy(
        tempo_worker_charm_url,
        application_name=worker_app,
        channel=worker_channel,
        trust=True,
    )
    app = await ops_test.model.deploy(
        tempo_coordinator_charm_url,
        application_name=tempo_app,
        channel=coordinator_channel,
        trust=True,
    )
    await ops_test.model.deploy("s3-integrator", channel="edge")
    await ops_test.model.integrate(tempo_app + ":s3", "s3-integrator" + ":s3-credentials")
    await ops_test.model.integrate(tempo_app + ":tempo-cluster", worker_app + ":tempo-cluster")
    await deploy_and_configure_minio(ops_test, get_unit_ips)

    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(
            apps=[tempo_app, worker_app, "s3-integrator"],
            status="active",
            timeout=2000,
            idle_period=30,
            # TODO: remove when https://github.com/canonical/tempo-coordinator-k8s-operator/issues/90 is fixed
            raise_on_error=False,
        )
    return app
