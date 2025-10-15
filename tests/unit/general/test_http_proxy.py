# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm unit tests for the http-proxy relation."""

import pathlib

import pytest
from charms.squid_forward_proxy.v0.http_proxy import ProxyConfig
from ops import testing

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from examples.springboot.charm.src.charm import SpringBootCharm
from paas_charm.app import App, WorkloadConfig
from paas_charm.charm_state import CharmState, IntegrationsState


@pytest.mark.parametrize(
    "framework_name, container_fixture_name",
    [
        pytest.param("django", "django_container_mock", id="django"),
        pytest.param("flask", "flask_container_mock", id="flask"),
        pytest.param("go", "go_container_mock", id="go"),
        pytest.param("springboot", "springboot_container_mock", id="springboot"),
        pytest.param("fastapi", "fastapi_container_mock", id="fastapi"),
        pytest.param("expressjs", "expressjs_container_mock", id="expressjs"),
    ],
)
@pytest.mark.parametrize(
    "set_env, integrations, expected",
    [
        pytest.param(
            {
                "JUJU_CHARM_HTTP_PROXY": "http://proxy.test",
                "JUJU_CHARM_HTTPS_PROXY": "http://proxy.test",
                "JUJU_CHARM_NO_PROXY": "127.0.0.1,localhost,::1",
            },
            None,
            {
                "APP_SECRET_KEY": "foobar",
                "APP_BASE_URL": "https://paas.example.com",
                "HTTP_PROXY": "http://proxy.test",
                "HTTPS_PROXY": "http://proxy.test",
                "NO_PROXY": "127.0.0.1,localhost,::1",
                "http_proxy": "http://proxy.test",
                "https_proxy": "http://proxy.test",
                "no_proxy": "127.0.0.1,localhost,::1",
            },
            id="no http proxy relation",
        ),
        pytest.param(
            {
                "JUJU_CHARM_HTTP_PROXY": "http://proxy.test",
                "JUJU_CHARM_HTTPS_PROXY": "http://proxy.test",
                "JUJU_CHARM_NO_PROXY": "127.0.0.1,localhost,::1",
            },
            IntegrationsState(
                http_proxy=ProxyConfig(
                    http_proxy="http://squid.internal:3128",
                    https_proxy="http://squid.internal:3128",
                )
            ),
            {
                "APP_SECRET_KEY": "foobar",
                "APP_BASE_URL": "https://paas.example.com",
                "HTTP_PROXY": "http://squid.internal:3128",
                "HTTPS_PROXY": "http://squid.internal:3128",
                "NO_PROXY": "127.0.0.1,localhost,::1",
                "http_proxy": "http://squid.internal:3128",
                "https_proxy": "http://squid.internal:3128",
                "no_proxy": "127.0.0.1,localhost,::1",
            },
            id="with http proxy relation",
        ),
    ],
)
def test_http_proxy(
    request,
    monkeypatch,
    framework_name,
    container_fixture_name,
    set_env,
    integrations,
    expected,
    database_migration_mock,
):
    """
    arrange: set juju charm generic app with and without http-proxy relation.
    act: generate an environment.
    assert: environment generated should contain proper proxy environment variables.
    """
    container_mock = request.getfixturevalue(container_fixture_name)
    for set_env_name, set_env_value in set_env.items():
        monkeypatch.setenv(set_env_name, set_env_value)

    base_dir = pathlib.Path("/app")
    workload_config = WorkloadConfig(
        framework=framework_name,
        container_name="app",
        port=8080,
        base_dir=base_dir,
        app_dir=base_dir,
        state_dir=base_dir / "state",
        service_name=framework_name,
        log_files=[],
        unit_name=f"{framework_name}/0",
    )

    charm_state = CharmState(
        framework=framework_name,
        secret_key="foobar",
        is_secret_storage_ready=True,
        framework_config={},
        base_url="https://paas.example.com",
        user_defined_config={},
        integrations=integrations,
    )

    app = App(
        container=container_mock,
        charm_state=charm_state,
        workload_config=workload_config,
        database_migration=database_migration_mock,
        framework_config_prefix="",
    )
    env = app.gen_environment()
    assert env == expected


@pytest.mark.parametrize(
    "base_state, charm, config",
    [
        pytest.param("flask_base_state", FlaskCharm, {}, id="flask"),
        pytest.param("django_base_state", DjangoCharm, {}, id="django"),
        pytest.param(
            "fastapi_base_state",
            FastAPICharm,
            {
                "non-optional-string": "test",
            },
            id="fastapi",
        ),
        pytest.param("spring_boot_base_state", SpringBootCharm, {}, id="spring-boot"),
        pytest.param("go_base_state", GoCharm, {}, id="go"),
        pytest.param("expressjs_base_state", ExpressJSCharm, {}, id="expressjs"),
    ],
)
def test_blocked_status_when_proxy_unavailable(
    base_state: dict, charm, config: dict, request
) -> None:
    """
    arrange: set the base state and add an empty http proxy relation.
    act: Run a config changed hook.
    assert: Workload charm should be blocked due to proxy values being unavailable.
    """

    base_state = request.getfixturevalue(base_state)
    base_state["config"] = config
    http_proxy_relation = testing.Relation(
        endpoint="http-proxy",
        interface="http_proxy",
        remote_app_data={},
    )
    base_state["relations"].append(http_proxy_relation)

    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=charm,
    )
    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(
        "http-proxy relation data is either unavailable, invalid or not usable."
    )
