# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pytest fixtures for the Flask unit tests."""

import pathlib
import typing
from unittest import mock

import pytest
import yaml
from ops import pebble, testing

from examples.flask.charm.src.charm import FlaskCharm
from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm.paas_config import PaasConfig, read_paas_config

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parents[3]
FLASK_CHARM_ROOT = PROJECT_ROOT / "examples" / "flask" / "charm"


@pytest.fixture(name="flask_context")
def flask_context_fixture(
    request: pytest.FixtureRequest,
) -> typing.Generator[testing.Context[FlaskCharm], None, None]:
    """Provide a lifecycle-managed Context rooted at the Flask example charm."""
    fixture_param = getattr(request, "param", None)
    unit_id = 0
    juju_version = "3.6.14"
    if isinstance(fixture_param, dict):
        paas_config = typing.cast(PaasConfig | None, fixture_param.get("paas_config"))
        unit_id = typing.cast(int, fixture_param.get("unit_id", 0))
        juju_version = typing.cast(str, fixture_param.get("juju_version", juju_version))
    else:
        paas_config = typing.cast(PaasConfig | None, fixture_param)
    if paas_config is None:
        paas_config = read_paas_config(FLASK_CHARM_ROOT)
    charmcraft = yaml.safe_load((FLASK_CHARM_ROOT / "charmcraft.yaml").read_text())
    actions = charmcraft.pop("actions")
    config = charmcraft.pop("config")
    with (
        mock.patch("paas_charm.charm.read_paas_config", return_value=paas_config),
        testing.Context(
            FlaskCharm,
            meta=charmcraft,
            actions=actions,
            config=config,
            charm_root=FLASK_CHARM_ROOT,
            unit_id=unit_id,
            juju_version=juju_version,
        ) as context,
    ):
        yield context


def flask_container(
    *,
    mount_source: pathlib.Path,
    base_plan: dict | None = None,
    execs: set[testing.Exec] | None = None,
    service_statuses: dict[str, pebble.ServiceStatus] | None = None,
) -> testing.Container:
    """Build a realistic Flask workload container."""
    mount_source.mkdir()
    state_source = mount_source.parent / "state"
    state_source.mkdir()
    return testing.Container(
        name="app",
        can_connect=True,
        execs=execs
        or {
            testing.Exec(["/bin/python3"], return_code=0),
            testing.Exec(["python3", "-c", "import gevent"], return_code=0),
        },
        mounts={
            "flask": testing.Mount(
                location="/flask",
                source=mount_source,
            ),
            "state": testing.Mount(
                location="/tmp/flask/state",
                source=state_source,
            ),
        },
        service_statuses=service_statuses or {"flask": pebble.ServiceStatus.INACTIVE},
        _base_plan=base_plan or DEFAULT_LAYER,
    )


@pytest.fixture(name="base_state")
def base_state_fixture(tmp_path: pathlib.Path) -> dict:
    """Return a leader Flask state with its container and peer relation."""
    return {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={"flask_secret_key": "test"},
            )
        ],
        "containers": {flask_container(mount_source=tmp_path / "flask")},
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(name="webserver")
def webserver_fixture(flask_container_mock):
    """Return a Gunicorn webserver backed by the focused container mock."""
    workload_config = create_workload_config(
        framework_name="flask",
        unit_name="flask/0",
        state_dir=pathlib.Path("/tmp/flask/state"),
    )
    return GunicornWebserver(
        webserver_config=WebserverConfig(),
        workload_config=workload_config,
        container=flask_container_mock,
    )
