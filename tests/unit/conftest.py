# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Global fixtures and utilities for unit tests."""

import copy
import io
import json
import typing
from contextlib import ExitStack
from pathlib import Path
from unittest import mock as unittest_mock
from unittest.mock import MagicMock

import ops
import pytest
import yaml
from ops import pebble, testing

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.charm import PaasCharm
from paas_charm.database_migration import DatabaseMigrationStatus
from paas_charm.paas_config import PaasConfig, read_paas_config
from tests.unit.django.constants import DEFAULT_LAYER as DJANGO_DEFAULT_LAYER
from tests.unit.expressjs.constants import DEFAULT_LAYER as EXPRESSJS_DEFAULT_LAYER
from tests.unit.fastapi.constants import DEFAULT_LAYER as FASTAPI_DEFAULT_LAYER
from tests.unit.flask.constants import DEFAULT_LAYER as FLASK_DEFAULT_LAYER
from tests.unit.go.constants import DEFAULT_LAYER as GO_DEFAULT_LAYER
from tests.unit.scenario import CHARM_ROOTS, FRAMEWORKS
from tests.unit.springboot.constants import DEFAULT_LAYER as SPRINGBOOT_DEFAULT_LAYER
from tests.unit.test_charm.src.charm import TestCharm

CONTAINER_NAME = "app"
GENERAL_DEFAULT_LAYERS = {
    FlaskCharm: {
        "services": {
            "flask": {
                "startup": "enabled",
                "override": "replace",
                "command": (
                    "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app -k [ sync ]"
                ),
            }
        }
    },
    DjangoCharm: {
        "services": {
            "django": {
                "startup": "enabled",
                "override": "replace",
                "command": (
                    "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py "
                    "django_app.wsgi:application -k [ sync ]"
                ),
            }
        }
    },
    FastAPICharm: {
        "services": {
            "fastapi": {
                "startup": "enabled",
                "override": "replace",
                "command": "/bin/python3 -m uvicorn app:app",
            }
        }
    },
    GoCharm: {
        "services": {
            "go": {
                "startup": "enabled",
                "override": "replace",
                "command": "go-app",
            }
        }
    },
    ExpressJSCharm: {
        "services": {
            "expressjs": {
                "startup": "enabled",
                "override": "replace",
                "command": "npm start",
            }
        }
    },
    SpringBootCharm: {
        "services": {
            "spring-boot": {
                "startup": "enabled",
                "override": "replace",
                "command": 'bash -c "java -jar *.jar"',
            }
        }
    },
}
TEST_DEFAULT_LAYER = {
    "services": {
        "app": {
            "override": "replace",
            "startup": "enabled",
            "command": "test-command",
            "user": "_daemon_",
        }
    }
}


@pytest.fixture
def container_name():
    """Return the container name."""
    return CONTAINER_NAME


@pytest.fixture
def database_migration_mock():
    """Create a mock instance for the DatabaseMigration class."""
    mock = MagicMock()
    mock.status = DatabaseMigrationStatus.PENDING
    mock.script = None
    return mock


@pytest.fixture
def flask_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(FLASK_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def django_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(DJANGO_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def go_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(GO_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def fastapi_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(FASTAPI_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def expressjs_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(EXPRESSJS_DEFAULT_LAYER["services"]))
    return container


@pytest.fixture
def springboot_container_mock():
    """Create a mock instance for the Container."""
    container = MagicMock(spec=ops.Container)
    container.pull.return_value = io.StringIO(json.dumps(SPRINGBOOT_DEFAULT_LAYER["services"]))
    return container


def postgresql_relation(db_name):
    """Postgresql relation fixture."""
    relation_data = {
        "database": db_name,
        "endpoints": "test-postgresql:5432",
        "password": "test-password",
        "username": "test-username",
    }
    return testing.Relation(
        endpoint="postgresql",
        interface="postgresql_client",
        remote_app_data=relation_data,
    )


def _add_oauth_metadata(charmcraft: dict) -> None:
    """Add a second OAuth integration to charmcraft metadata."""
    charmcraft["requires"]["google"] = {
        "interface": "oauth",
        "optional": True,
        "limit": 1,
    }
    charmcraft["config"]["options"].update(
        {
            "google-redirect-path": {
                "default": "/callback",
                "description": "The OAuth redirect path.",
                "type": "string",
            },
            "google-scopes": {
                "default": "openid profile email",
                "description": "Space-separated OAuth scopes.",
                "type": "string",
            },
            "google-user-name-attribute": {
                "default": "email",
                "description": "The OAuth user name attribute.",
                "type": "string",
            },
        }
    )


@pytest.fixture(name="context_factory")
def context_factory_fixture(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> typing.Callable[..., testing.Context]:
    """Create lifecycle-managed Contexts rooted at their example charms."""
    stack = ExitStack()
    request.addfinalizer(stack.close)
    context_count = 0

    def _factory(
        charm_type: type,
        *,
        paas_config: PaasConfig | None = None,
        additional_oauth: bool = False,
        no_database_metadata: bool = False,
        unit_id: int = 0,
        juju_version: str = "3.6.14",
    ) -> testing.Context:
        nonlocal context_count
        context_count += 1
        root = CHARM_ROOTS[charm_type]
        resolved_paas_config = paas_config if paas_config is not None else read_paas_config(root)
        charmcraft = yaml.safe_load((root / "charmcraft.yaml").read_text(encoding="utf-8"))
        if additional_oauth:
            _add_oauth_metadata(charmcraft)
        if no_database_metadata:
            charmcraft["requires"].pop("postgresql")
        context_root = tmp_path / "contexts" / f"{root.parent.name}-{context_count}"
        context_root.mkdir(parents=True)
        (context_root / "charmcraft.yaml").write_text(yaml.safe_dump(charmcraft), encoding="utf-8")
        context_kwargs: dict[str, object] = {
            "actions": charmcraft.pop("actions", {}),
            "config": charmcraft.pop("config", {}),
            "meta": charmcraft,
        }
        stack.enter_context(
            unittest_mock.patch(
                "paas_charm.charm.read_paas_config",
                return_value=resolved_paas_config,
            )
        )
        return stack.enter_context(
            testing.Context(
                charm_type,
                charm_root=context_root,
                unit_id=unit_id,
                juju_version=juju_version,
                **context_kwargs,
            )
        )

    return _factory


@pytest.fixture(name="flask_context")
def flask_context_fixture(
    request: pytest.FixtureRequest,
    context_factory,
) -> testing.Context[FlaskCharm]:
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
    return context_factory(
        FlaskCharm,
        paas_config=paas_config,
        unit_id=unit_id,
        juju_version=juju_version,
    )


@pytest.fixture(name="django_context")
def django_context_fixture(
    request: pytest.FixtureRequest,
    context_factory,
) -> testing.Context[DjangoCharm]:
    """Provide a lifecycle-managed Context rooted at the Django example charm."""
    return context_factory(
        DjangoCharm,
        no_database_metadata=getattr(request, "param", None) == "no-database-metadata",
    )


@pytest.fixture(name="fastapi_context")
def fastapi_context_fixture(
    request: pytest.FixtureRequest,
    context_factory,
) -> testing.Context[FastAPICharm]:
    """Provide a lifecycle-managed Context rooted at the FastAPI example charm."""
    return context_factory(
        FastAPICharm,
        paas_config=typing.cast(PaasConfig | None, getattr(request, "param", None)),
    )


@pytest.fixture(name="go_context")
def go_context_fixture(context_factory) -> testing.Context[GoCharm]:
    """Provide a lifecycle-managed Context rooted at the Go example charm."""
    return context_factory(GoCharm)


@pytest.fixture(name="expressjs_context")
def expressjs_context_fixture(context_factory) -> testing.Context[ExpressJSCharm]:
    """Provide a lifecycle-managed Context rooted at the ExpressJS example charm."""
    return context_factory(ExpressJSCharm)


@pytest.fixture(name="springboot_context")
def springboot_context_fixture(context_factory) -> testing.Context[SpringBootCharm]:
    """Provide a lifecycle-managed Context rooted at the Spring Boot example charm."""
    return context_factory(SpringBootCharm)


@pytest.fixture(name="generic_context")
def generic_context_fixture(context_factory) -> testing.Context:
    """Return a Context rooted at the generic test charm."""
    return context_factory(TestCharm)


def flask_container(
    *,
    mount_source: Path,
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
            "flask": testing.Mount(location="/flask", source=mount_source),
            "state": testing.Mount(location="/tmp/flask/state", source=state_source),
        },
        service_statuses=service_statuses or {"flask": pebble.ServiceStatus.INACTIVE},
        _base_plan=base_plan or FLASK_DEFAULT_LAYER,
    )


def django_container(
    *,
    mount_source: Path,
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
        _base_plan=base_plan if base_plan is not None else DJANGO_DEFAULT_LAYER,
    )


def _django_state(*, mount_source: Path, with_database: bool) -> dict:
    """Build a Django state, optionally with PostgreSQL."""
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


@pytest.fixture(name="flask_framework_state")
def flask_framework_state_fixture(tmp_path: Path) -> dict:
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


@pytest.fixture(name="django_framework_state")
def django_framework_state_fixture(tmp_path: Path) -> dict:
    """Return a Django state with its required PostgreSQL integration."""
    return _django_state(mount_source=tmp_path / "django", with_database=True)


@pytest.fixture(name="django_framework_state_no_database")
def django_framework_state_no_database_fixture(tmp_path: Path) -> dict:
    """Return a Django state without a database integration."""
    return _django_state(mount_source=tmp_path / "django", with_database=False)


@pytest.fixture(name="fastapi_framework_state")
def fastapi_framework_state_fixture() -> dict:
    """Return the framework-focused FastAPI state."""
    return {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={"fastapi_secret_key": "test"},
            )
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                _base_plan=FASTAPI_DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
        "config": {"non-optional-string": "non-optional-value"},
    }


@pytest.fixture(name="go_framework_state")
def go_framework_state_fixture() -> dict:
    """Return the framework-focused Go state."""
    return {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={"go_secret_key": "test"},
            )
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                _base_plan=GO_DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(name="expressjs_framework_state")
def expressjs_framework_state_fixture() -> dict:
    """Return the framework-focused ExpressJS state."""
    return {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={"expressjs_secret_key": "test"},
            ),
            postgresql_relation("test-database"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                _base_plan=EXPRESSJS_DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(name="spring_boot_framework_state")
def spring_boot_framework_state_fixture(tmp_path: Path) -> dict:
    """Return the framework-focused Spring Boot state."""
    certificate = tmp_path / "spring-boot" / "saml.cert"
    certificate.parent.mkdir()
    certificate.touch()
    return {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={"spring-boot_secret_key": "test"},
            ),
            postgresql_relation("spring-boot-k8s"),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/app/saml.cert", source=certificate)},
                _base_plan=SPRINGBOOT_DEFAULT_LAYER,
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(name="framework_state_factory")
def framework_state_factory_fixture(tmp_path: Path) -> typing.Callable[..., dict]:
    """Build fresh uniform states for parameterized cross-framework tests."""
    counter = 0

    def _factory(charm_type: type, *, config: dict | None = None) -> dict:
        nonlocal counter
        counter += 1
        framework = FRAMEWORKS[charm_type]
        relations: list[testing.Relation | testing.PeerRelation] = [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={f"{framework}_secret_key": "test"},
            )
        ]
        if charm_type in {
            DjangoCharm,
            FastAPICharm,
            GoCharm,
            ExpressJSCharm,
            SpringBootCharm,
        }:
            relations.append(postgresql_relation(f"{framework}-k8s"))

        state_dir = tmp_path / f"{framework}-{counter}"
        state_dir.mkdir()
        mounts = {}
        execs = set()
        if charm_type in {FlaskCharm, DjangoCharm}:
            gunicorn_config = state_dir / "gunicorn.conf.py"
            gunicorn_config.touch()
            mounts["config"] = testing.Mount(
                location=f"/{framework}/gunicorn.conf.py",
                source=gunicorn_config,
            )
            execs.add(testing.Exec(command_prefix=["/bin/python3"], return_code=0))
        elif charm_type is FastAPICharm:
            execs.add(testing.Exec(command_prefix=["/bin/python3"], return_code=0))
        elif charm_type is GoCharm:
            execs.add(testing.Exec(command_prefix=["go-app"], return_code=0))
        elif charm_type is SpringBootCharm:
            certificate = state_dir / "saml.cert"
            certificate.touch()
            mounts["certificate"] = testing.Mount(
                location="/app/saml.cert",
                source=certificate,
            )

        state_config = copy.deepcopy(config or {})
        if charm_type is FastAPICharm:
            state_config.setdefault("non-optional-string", "non-optional-value")
        return {
            "leader": True,
            "relations": relations,
            "containers": {
                testing.Container(
                    name="app",
                    can_connect=True,
                    mounts=mounts,
                    execs=execs,
                    _base_plan=copy.deepcopy(GENERAL_DEFAULT_LAYERS[charm_type]),
                )
            },
            "config": state_config,
            "model": testing.Model(name="test-model"),
        }

    return _factory


@pytest.fixture(name="generic_state")
def generic_state_fixture(tmp_path: Path) -> dict:
    """Return a state for the generic test charm."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    return {
        "leader": True,
        "relations": [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={"test_secret_key": "test"},
            )
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                mounts={"app": testing.Mount(location="/app", source=app_dir)},
                _base_plan=copy.deepcopy(TEST_DEFAULT_LAYER),
            )
        },
        "model": testing.Model(name="test-model"),
    }


@pytest.fixture(name="flask_base_state")
def flask_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh Flask state for cross-framework tests."""
    return framework_state_factory(FlaskCharm)


@pytest.fixture(name="django_base_state")
def django_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh Django state for cross-framework tests."""
    return framework_state_factory(DjangoCharm)


@pytest.fixture(name="fastapi_base_state")
def fastapi_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh FastAPI state for cross-framework tests."""
    return framework_state_factory(FastAPICharm)


@pytest.fixture(name="go_base_state")
def go_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh Go state for cross-framework tests."""
    return framework_state_factory(GoCharm)


@pytest.fixture(name="expressjs_base_state")
def expressjs_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh ExpressJS state for cross-framework tests."""
    return framework_state_factory(ExpressJSCharm)


@pytest.fixture(name="spring_boot_base_state")
def spring_boot_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh Spring Boot state for cross-framework tests."""
    return framework_state_factory(SpringBootCharm)


@pytest.fixture(autouse=True)
def temp_cos_merged_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Store merged COS assets in a test temporary directory."""

    def _get_cos_merged_dir(_: PaasCharm) -> Path:
        return (tmp_path / "cos_merged").absolute()

    monkeypatch.setattr(PaasCharm, "get_cos_merged_dir", _get_cos_merged_dir)
