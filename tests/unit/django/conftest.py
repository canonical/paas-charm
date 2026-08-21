# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Pytest fixtures for the Django unit tests."""

import pathlib
import typing
from unittest import mock

import pytest
import yaml
from ops import pebble, testing

from examples.django.charm.src.charm import DjangoCharm
from paas_charm.paas_config import read_paas_config
from tests.unit.conftest import postgresql_relation

from .constants import DEFAULT_LAYER

PROJECT_ROOT = pathlib.Path(__file__).parents[3]
DJANGO_CHARM_ROOT = PROJECT_ROOT / "examples" / "django" / "charm"


@pytest.fixture(name="django_context")
def django_context_fixture(
    request: pytest.FixtureRequest,
) -> typing.Generator[testing.Context[DjangoCharm], None, None]:
    """Provide a lifecycle-managed Context rooted at the Django example charm."""
    charmcraft = yaml.safe_load(
        (DJANGO_CHARM_ROOT / "charmcraft.yaml").read_text(encoding="utf-8")
    )
    actions = charmcraft.pop("actions")
    config = charmcraft.pop("config")
    if getattr(request, "param", None) == "no-database-metadata":
        charmcraft["requires"].pop("postgresql")
    with (
        mock.patch(
            "paas_charm.charm.read_paas_config",
            return_value=read_paas_config(DJANGO_CHARM_ROOT),
        ),
        testing.Context(
            DjangoCharm,
            meta=charmcraft,
            actions=actions,
            config=config,
            charm_root=DJANGO_CHARM_ROOT,
        ) as context,
    ):
        yield context


def django_container(
    *,
    mount_source: pathlib.Path,
    base_plan: dict | None = None,
    execs: set[testing.Exec] | None = None,
) -> testing.Container:
    """Build a realistic Django workload container."""
    mount_source.mkdir()
    state_source = mount_source.parent / "state"
    state_source.mkdir()
    return testing.Container(
        name="app",
        can_connect=True,
        mounts={
            "django": testing.Mount(location="/django", source=mount_source),
            "state": testing.Mount(location="/tmp/django/state", source=state_source),
        },
        execs=(
            execs
            if execs is not None
            else {
                testing.Exec(["/bin/python3"], return_code=0),
                testing.Exec(["python3", "-c", "import gevent"], return_code=0),
                testing.Exec(
                    ["python3", "manage.py", "createsuperuser", "--noinput"],
                    stdout="OK",
                ),
            }
        ),
        service_statuses={"django": pebble.ServiceStatus.INACTIVE},
        _base_plan=base_plan if base_plan is not None else DEFAULT_LAYER,
    )


def _base_state(*, mount_source: pathlib.Path, with_database: bool) -> dict:
    """Build the shared Scenario state, optionally with PostgreSQL."""
    relations: list[testing.RelationBase] = [
        testing.PeerRelation(
            "secret-storage",
            local_app_data={"django_secret_key": "test"},
        )
    ]
    if with_database:
        relations.append(postgresql_relation("django-k8s"))
    return {
        "relations": relations,
        "containers": {django_container(mount_source=mount_source)},
        "leader": True,
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(name="base_state")
def base_state_fixture(tmp_path: pathlib.Path) -> dict:
    """Return a Django state with its required PostgreSQL integration."""
    return _base_state(mount_source=tmp_path / "django", with_database=True)


@pytest.fixture(name="base_state_no_database")
def base_state_no_database_fixture(tmp_path: pathlib.Path) -> dict:
    """Return a Django state without a database integration."""
    return _base_state(mount_source=tmp_path / "django", with_database=False)
