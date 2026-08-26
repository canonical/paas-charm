# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Django charm unit tests."""

# this is a unit test file
# pylint: disable=protected-access

import dataclasses

import pytest
from ops import testing

BASE_DJANGO_ENV = {
    "DJANGO_OIDC_REDIRECT_PATH": "/callback",
    "DJANGO_OIDC_SCOPES": "openid profile email",
    "DJANGO_SECRET_KEY": "test",
    "DJANGO_ALLOWED_HOSTS": '["django-k8s.test-model"]',
    "DJANGO_METRICS_PORT": "9102",
    "DJANGO_METRICS_PATH": "/metrics",
    "DJANGO_BASE_URL": "http://django-k8s.test-model:8000",
    "POSTGRESQL_DB_CONNECT_STRING": (
        "postgresql://test-username:test-password@test-postgresql:5432/django-k8s"
    ),
    "POSTGRESQL_DB_SCHEME": "postgresql",
    "POSTGRESQL_DB_NETLOC": "test-username:test-password@test-postgresql:5432",
    "POSTGRESQL_DB_PATH": "/django-k8s",
    "POSTGRESQL_DB_PARAMS": "",
    "POSTGRESQL_DB_QUERY": "",
    "POSTGRESQL_DB_FRAGMENT": "",
    "POSTGRESQL_DB_USERNAME": "test-username",
    "POSTGRESQL_DB_PASSWORD": "test-password",
    "POSTGRESQL_DB_HOSTNAME": "test-postgresql",
    "POSTGRESQL_DB_PORT": "5432",
    "POSTGRESQL_DB_NAME": "django-k8s",
}

TEST_DJANGO_CONFIG_PARAMS = [
    pytest.param(
        {},
        BASE_DJANGO_ENV,
        id="default",
    ),
    pytest.param(
        {"django-allowed-hosts": "test.local"},
        {
            **BASE_DJANGO_ENV,
            "DJANGO_ALLOWED_HOSTS": '["test.local", "django-k8s.test-model"]',
        },
        id="allowed-hosts",
    ),
    pytest.param(
        {"django-debug": True},
        {
            **BASE_DJANGO_ENV,
            "DJANGO_DEBUG": "true",
        },
        id="debug",
    ),
    pytest.param(
        {"app-secret-key": "foobar"},
        {
            **BASE_DJANGO_ENV,
            "DJANGO_SECRET_KEY": "foobar",
        },
        id="secret-key",
    ),
]


def _assert_django_service(service, expected_env: dict, worker_class: str) -> None:
    """Assert the complete Django service plan."""
    assert service.to_dict() == {
        "environment": expected_env,
        "override": "replace",
        "startup": "enabled",
        "command": (
            "/bin/python3 -m gunicorn -c /var/lib/gunicorn/gunicorn.conf.py "
            f"django_app.wsgi:application -k [ {worker_class} ]"
        ),
        "after": ["statsd-exporter"],
        "user": "_daemon_",
    }


@pytest.mark.parametrize("config, env", TEST_DJANGO_CONFIG_PARAMS)
def test_django_config(
    django_context,
    base_state: dict,
    container_name: str,
    config: dict,
    env: dict,
) -> None:
    """
    arrange: none
    act: start the django charm and set app container to be ready.
    assert: django charm should submit the correct pebble layer to pebble.
    """
    state = testing.State(**{**base_state, "config": config})

    out = django_context.run(django_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    service = out.get_container(container_name).plan.services["django"]
    _assert_django_service(service, env, "sync")
    assert len(out.get_relations("postgresql")) == 1


def test_django_create_super_user(django_context, base_state: dict, container_name: str) -> None:
    """
    arrange: Start the Django charm. Mock the Django command (pebble exec) to create a superuser.
    act: Run action create superuser.
    assert: The action is called with the right arguments, returning a password for the user.
    """
    state = testing.State(**base_state)

    django_context.run(
        django_context.on.action(
            "create-superuser",
            params={"username": "admin", "email": "admin@example.com"},
        ),
        state,
    )

    exec_args = next(
        args
        for args in django_context.exec_history[container_name]
        if args.command == ["python3", "manage.py", "createsuperuser", "--noinput"]
    )
    assert exec_args.environment["DJANGO_SUPERUSER_USERNAME"] == "admin"
    assert exec_args.environment["DJANGO_SUPERUSER_EMAIL"] == "admin@example.com"
    assert "DJANGO_SECRET_KEY" in exec_args.environment
    assert exec_args.working_dir == "/app"
    assert django_context.action_results == {
        "password": exec_args.environment["DJANGO_SUPERUSER_PASSWORD"]
    }


def test_django_create_super_user_exec_failure(django_context, base_state: dict) -> None:
    """
    arrange: configure the create-superuser command to fail.
    act: run the create-superuser action.
    assert: the action fails with the command output.
    """
    container = dataclasses.replace(
        next(iter(base_state["containers"])),
        execs={
            testing.Exec(["/bin/python3"], return_code=0),
            testing.Exec(
                ["python3", "manage.py", "createsuperuser", "--noinput"],
                return_code=1,
                stdout="username already exists",
            ),
        },
    )
    state = testing.State(**{**base_state, "containers": {container}})

    with pytest.raises(testing.ActionFailed, match="username already exists"):
        django_context.run(
            django_context.on.action(
                "create-superuser",
                params={"username": "admin", "email": "admin@example.com"},
            ),
            state,
        )


@pytest.mark.parametrize("django_context", ["no-database-metadata"], indirect=True)
def test_required_database_integration(django_context, base_state_no_database: dict):
    """
    arrange: Start the Django charm with no integrations specified in the charm.
    act: Start the django charm and set app container to be ready.
    assert: The charm should be blocked, as Django requires a database to work.
    """
    state = testing.State(**base_state_no_database)

    out = django_context.run(django_context.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Django requires a database integration to work"
    )


@pytest.mark.parametrize("config, env", TEST_DJANGO_CONFIG_PARAMS)
def test_django_async_config(
    django_context,
    base_state: dict,
    container_name: str,
    config: dict,
    env: dict,
) -> None:
    """
    arrange: None
    act: Start the django charm and set app container to be ready.
    assert: Django charm should submit the correct pebble layer to pebble.
    """
    state = testing.State(
        **{**base_state, "config": {**config, "webserver-worker-class": "gevent"}}
    )

    out = django_context.run(django_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    service = out.get_container(container_name).plan.services["django"]
    _assert_django_service(service, env, "gevent")


def test_allowed_hosts_deduplicates_when_configured_host_matches_ingress(
    django_context,
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
    out = django_context.run(django_context.on.config_changed(), state)

    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["django-k8s.test-model"]'

    ingress = testing.Relation(
        endpoint="ingress",
        interface="ingress",
        remote_app_data={"ingress": '{"url": "https://django-k8s.test-model/"}'},
    )
    state = dataclasses.replace(out, relations={*out.relations, ingress})
    out = django_context.run(django_context.on.relation_changed(ingress), state)

    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["django-k8s.test-model"]'


def test_allowed_hosts_base_hostname_updates_correctly(
    django_context,
    base_state: dict,
    container_name: str,
):
    """
    arrange: Deploy a Django charm without an ingress integration
    act: Add a new ingress integration
    assert: The allowed hosts env var should match the url of the ingress integration
    act: Update the url in the ingress integration
    assert: The allowed hosts env var should match the new url of the ingress integration
    """
    base_state["model"] = testing.Model(name="flask-model")
    state = testing.State(**base_state)
    out = django_context.run(django_context.on.config_changed(), state)

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
    out = django_context.run(django_context.on.relation_changed(ingress), state)

    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["oldjuju.test"]'

    # Updating the ingress url to a new url should update the allowed hosts.
    updated_ingress = dataclasses.replace(
        ingress,
        remote_app_data={"ingress": '{"url": "http://newjuju.test/"}'},
    )
    relations = {relation for relation in out.relations if relation.id != ingress.id}
    state = dataclasses.replace(out, relations={*relations, updated_ingress})
    out = django_context.run(django_context.on.relation_changed(updated_ingress), state)

    env = out.get_container(container_name).plan.services["django"].environment
    assert env["DJANGO_ALLOWED_HOSTS"] == '["newjuju.test"]'


def test_real_paas_config_enables_structured_logging(
    django_context,
    base_state: dict,
    container_name: str,
) -> None:
    """
    arrange: use the real Django paas-config with JSON framework logging.
    act: reconcile the charm.
    assert: the generated Gunicorn config installs the structured logger and middleware.
    """
    out = django_context.run(
        django_context.on.config_changed(),
        testing.State(**base_state),
    )

    filesystem = out.get_container(container_name).get_filesystem(django_context)
    config = (filesystem / "var" / "lib" / "gunicorn" / "gunicorn.conf.py").read_text(
        encoding="utf-8"
    )
    assert "class GunicornJsonFormatter(logging.Formatter):" in config
    assert "class GunicornJsonLogger(glogging.Logger):" in config
    assert "logger_class = GunicornJsonLogger" in config
    assert "worker.app.wsgi = _patched_wsgi" in config
