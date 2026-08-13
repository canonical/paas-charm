# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Django charm unit tests."""

# this is a unit test file
# pylint: disable=protected-access

import dataclasses
import pathlib

import pytest
import yaml
from ops import testing

from examples.django.charm.src.charm import DjangoCharm

CHARMCRAFT_CONFIG = yaml.safe_load(
    (
        pathlib.Path(__file__).parents[3] / "examples" / "django" / "charm" / "charmcraft.yaml"
    ).read_text(encoding="utf-8")
)["config"]
NO_DATABASE_META = {
    "name": "django-k8s",
    "containers": {"app": {"resource": "app-image"}},
    "peers": {"secret-storage": {"interface": "secret-storage"}},
    "provides": {
        "grafana-dashboard": {"interface": "grafana_dashboard"},
        "metrics-endpoint": {"interface": "prometheus_scrape"},
    },
    "requires": {
        "ingress": {"interface": "ingress", "limit": 1},
        "logging": {"interface": "loki_push_api"},
    },
}
DJANGO_ACTIONS = {
    "rotate-secret-key": {},
    "create-superuser": {
        "params": {
            "username": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["username", "email"],
    },
}

TEST_DJANGO_CONFIG_PARAMS = [
    pytest.param(
        {},
        {
            "DJANGO_OIDC_REDIRECT_PATH": "/callback",
            "DJANGO_OIDC_SCOPES": "openid profile email",
            "DJANGO_SECRET_KEY": "test",
            "DJANGO_ALLOWED_HOSTS": '["django-k8s.test-model"]',
        },
        id="default",
    ),
    pytest.param(
        {"django-allowed-hosts": "test.local"},
        {
            "DJANGO_OIDC_REDIRECT_PATH": "/callback",
            "DJANGO_OIDC_SCOPES": "openid profile email",
            "DJANGO_SECRET_KEY": "test",
            "DJANGO_ALLOWED_HOSTS": '["test.local", "django-k8s.test-model"]',
        },
        id="allowed-hosts",
    ),
    pytest.param(
        {"django-debug": True},
        {
            "DJANGO_OIDC_REDIRECT_PATH": "/callback",
            "DJANGO_OIDC_SCOPES": "openid profile email",
            "DJANGO_SECRET_KEY": "test",
            "DJANGO_ALLOWED_HOSTS": '["django-k8s.test-model"]',
            "DJANGO_DEBUG": "true",
        },
        id="debug",
    ),
    pytest.param(
        {"django-secret-key": "foobar"},
        {
            "DJANGO_OIDC_REDIRECT_PATH": "/callback",
            "DJANGO_OIDC_SCOPES": "openid profile email",
            "DJANGO_SECRET_KEY": "foobar",
            "DJANGO_ALLOWED_HOSTS": '["django-k8s.test-model"]',
        },
        id="secret-key",
    ),
]


@pytest.mark.parametrize("config, env", TEST_DJANGO_CONFIG_PARAMS)
def test_django_config(base_state: dict, container_name: str, config: dict, env: dict) -> None:
    """
    arrange: none
    act: start the django charm and set app container to be ready.
    assert: django charm should submit the correct pebble layer to pebble.
    """
    state = testing.State(**{**base_state, "config": config})
    context = testing.Context(DjangoCharm)

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    service = out.get_container(container_name).plan.services["django"]
    for key, value in env.items():
        assert service.environment[key] == value
    assert (
        service.command == "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py "
        "django_app.wsgi:application -k [ sync ]"
    )


def test_django_create_super_user(base_state: dict, container_name: str) -> None:
    """
    arrange: Start the Django charm. Mock the Django command (pebble exec) to create a superuser.
    act: Run action create superuser.
    assert: The action is called with the right arguments, returning a password for the user.
    """
    state = testing.State(**base_state)
    context = testing.Context(DjangoCharm)

    context.run(
        context.on.action(
            "create-superuser",
            params={"username": "admin", "email": "admin@example.com"},
        ),
        state,
    )

    exec_args = next(
        args
        for args in context.exec_history[container_name]
        if args.command == ["python3", "manage.py", "createsuperuser", "--noinput"]
    )
    assert exec_args.environment["DJANGO_SUPERUSER_USERNAME"] == "admin"
    assert exec_args.environment["DJANGO_SUPERUSER_EMAIL"] == "admin@example.com"
    assert "DJANGO_SECRET_KEY" in exec_args.environment
    assert context.action_results is not None
    assert context.action_results["password"] == exec_args.environment["DJANGO_SUPERUSER_PASSWORD"]


def test_required_database_integration(base_state_no_database: dict):
    """
    arrange: Start the Django charm with no integrations specified in the charm.
    act: Start the django charm and set app container to be ready.
    assert: The charm should be blocked, as Django requires a database to work.
    """
    state = testing.State(**base_state_no_database)
    context = testing.Context(
        DjangoCharm,
        meta=NO_DATABASE_META,
        actions=DJANGO_ACTIONS,
        config=CHARMCRAFT_CONFIG,
    )

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Django requires a database integration to work"
    )


@pytest.mark.parametrize("config, env", TEST_DJANGO_CONFIG_PARAMS)
def test_django_async_config(
    base_state: dict, container_name: str, config: dict, env: dict
) -> None:
    """
    arrange: None
    act: Start the django charm and set app container to be ready.
    assert: Django charm should submit the correct pebble layer to pebble.
    """
    state = testing.State(
        **{**base_state, "config": {**config, "webserver-worker-class": "gevent"}}
    )
    context = testing.Context(DjangoCharm)

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    service = out.get_container(container_name).plan.services["django"]
    for key, value in env.items():
        assert service.environment[key] == value
    assert (
        service.command == "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py "
        "django_app.wsgi:application -k [ gevent ]"
    )


def test_allowed_hosts_deduplicates_when_configured_host_matches_ingress(
    base_state: dict,
    container_name: str,
):
    """
    arrange: Configure the django charm with an allowed host that matches the ingress url hostname.
    act: Start the django charm and add an ingress relation.
    assert: The allowed hosts should not contain duplicates.
    """
    state = testing.State(
        **{**base_state, "config": {"django-allowed-hosts": "django-k8s.test-model"}}
    )
    context = testing.Context(DjangoCharm)
    out = context.run(context.on.config_changed(), state)

    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["django-k8s.test-model"]'

    ingress = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "https://django-k8s.test-model/"}'},
    )
    state = dataclasses.replace(out, relations={*out.relations, ingress})
    out = context.run(context.on.relation_changed(ingress), state)

    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["django-k8s.test-model"]'


def test_allowed_hosts_base_hostname_updates_correctly(base_state: dict, container_name: str):
    """
    arrange: Deploy a Django charm without an ingress integration
    act: Add a new ingress integration
    assert: The allowed hosts env var should match the url of the ingress integration
    act: Update the url in the ingress integration
    assert: The allowed hosts env var should match the new url of the ingress integration
    """
    base_state["model"] = testing.Model(name="flask-model")
    state = testing.State(**base_state)
    context = testing.Context(DjangoCharm)
    out = context.run(context.on.config_changed(), state)

    # The initial allowed hosts matches the k8s service name.
    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["django-k8s.flask-model"]'

    # Add a relation and the allowed hosts should be updated to the ingress url
    ingress = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "http://oldjuju.test/"}'},
    )
    state = dataclasses.replace(out, relations={*out.relations, ingress})
    out = context.run(context.on.relation_changed(ingress), state)

    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["oldjuju.test"]'

    # Updating the ingress url to a new url should update the allowed hosts.
    updated_ingress = dataclasses.replace(
        ingress,
        remote_app_data={"ingress": '{"url": "http://newjuju.test/"}'},
    )
    relations = {relation for relation in out.relations if relation.id != ingress.id}
    state = dataclasses.replace(out, relations={*relations, updated_ingress})
    out = context.run(context.on.relation_changed(updated_ingress), state)

    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["newjuju.test"]'
