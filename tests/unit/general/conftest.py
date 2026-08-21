# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""Shared Scenario fixtures for the general unit tests."""

import copy
import pathlib
import typing
from contextlib import ExitStack
from unittest import mock

import pytest
import yaml
from ops import testing

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.paas_config import PaasConfig, read_paas_config
from tests.unit.conftest import postgresql_relation
from tests.unit.test_charm.src.charm import TestCharm

PROJECT_ROOT = pathlib.Path(__file__).parents[3]
TEST_CHARM_ROOT = PROJECT_ROOT / "tests/unit/test_charm"
CHARM_ROOTS = {
    TestCharm: TEST_CHARM_ROOT,
    FlaskCharm: PROJECT_ROOT / "examples/flask/charm",
    DjangoCharm: PROJECT_ROOT / "examples/django/charm",
    FastAPICharm: PROJECT_ROOT / "examples/fastapi/charm",
    GoCharm: PROJECT_ROOT / "examples/go/charm",
    ExpressJSCharm: PROJECT_ROOT / "examples/expressjs/charm",
    SpringBootCharm: PROJECT_ROOT / "examples/springboot/charm",
}
FRAMEWORKS = {
    FlaskCharm: "flask",
    DjangoCharm: "django",
    FastAPICharm: "fastapi",
    GoCharm: "go",
    ExpressJSCharm: "expressjs",
    SpringBootCharm: "spring-boot",
}
DEFAULT_LAYERS = {
    FlaskCharm: {
        "services": {
            "flask": {
                "startup": "enabled",
                "override": "replace",
                "command": (
                    "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py " "app:app -k [ sync ]"
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


def charm_root(charm_type: type) -> pathlib.Path:
    """Return the explicit charm root for a test charm type."""
    return CHARM_ROOTS[charm_type]


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
    tmp_path: pathlib.Path,
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
    ) -> testing.Context:
        nonlocal context_count
        context_count += 1
        root = charm_root(charm_type)
        resolved_paas_config = paas_config if paas_config is not None else read_paas_config(root)
        context_root = root
        context_kwargs = {}
        if additional_oauth:
            context_root = tmp_path / "contexts" / f"{root.parent.name}-{context_count}"
            context_root.mkdir(parents=True)
            charmcraft = yaml.safe_load((root / "charmcraft.yaml").read_text())
            _add_oauth_metadata(charmcraft)
            (context_root / "charmcraft.yaml").write_text(yaml.safe_dump(charmcraft))
            context_kwargs = {
                "actions": charmcraft.pop("actions", {}),
                "config": charmcraft.pop("config", {}),
                "meta": charmcraft,
            }
        stack.enter_context(
            mock.patch("paas_charm.charm.read_paas_config", return_value=resolved_paas_config)
        )
        return stack.enter_context(
            testing.Context(
                charm_type,
                charm_root=context_root,
                **context_kwargs,
            )
        )

    return _factory


@pytest.fixture(name="generic_context")
def generic_context_fixture(context_factory) -> testing.Context:
    """Return a Context rooted at the generic test charm."""
    return context_factory(TestCharm)


@pytest.fixture(name="framework_state_factory")
def framework_state_factory_fixture(tmp_path: pathlib.Path) -> typing.Callable[..., dict]:
    """Build fresh realistic states for parameterized framework tests."""
    counter = 0

    def _factory(charm_type: type, *, config: dict | None = None) -> dict:
        nonlocal counter
        counter += 1
        framework = FRAMEWORKS[charm_type]
        peer_key = f"{framework}_secret_key"
        relations: list[testing.Relation | testing.PeerRelation] = [
            testing.PeerRelation(
                "secret-storage",
                local_app_data={peer_key: "test"},
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
                    _base_plan=copy.deepcopy(DEFAULT_LAYERS[charm_type]),
                )
            },
            "config": state_config,
            "model": testing.Model(name="test-model"),
        }

    return _factory


@pytest.fixture(name="generic_state")
def generic_state_fixture(tmp_path: pathlib.Path) -> dict:
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
    """Return a fresh Flask state."""
    return framework_state_factory(FlaskCharm)


@pytest.fixture(name="django_base_state")
def django_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh Django state."""
    return framework_state_factory(DjangoCharm)


@pytest.fixture(name="fastapi_base_state")
def fastapi_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh FastAPI state."""
    return framework_state_factory(FastAPICharm)


@pytest.fixture(name="go_base_state")
def go_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh Go state."""
    return framework_state_factory(GoCharm)


@pytest.fixture(name="expressjs_base_state")
def expressjs_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh ExpressJS state."""
    return framework_state_factory(ExpressJSCharm)


@pytest.fixture(name="spring_boot_base_state")
def spring_boot_base_state_fixture(framework_state_factory) -> dict:
    """Return a fresh Spring Boot state."""
    return framework_state_factory(SpringBootCharm)


OAUTH_RELATION_DATA_EXAMPLE = {
    "authorization_endpoint": "https://traefik_ip/model_name-hydra/oauth2/auth",
    "introspection_endpoint": "http://hydra.model_name.svc.cluster.local:4445/admin/oauth2/introspect",
    "issuer_url": "https://traefik_ip/model_name-hydra",
    "jwks_endpoint": "https://traefik_ip/model_name-hydra/.well-known/jwks.json",
    "scope": "openid profile email",
    "token_endpoint": "https://traefik_ip/model_name-hydra/oauth2/token",
    "userinfo_endpoint": "https://traefik_ip/model_name-hydra/userinfo",
    "client_id": "test-client-id",
}
