#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Django charm."""

import jubilant
import pytest
import requests

from tests.integration.types import App


@pytest.mark.parametrize(
    "update_config, timeout",
    [
        pytest.param({"webserver-timeout": 7}, 7, id="timeout=7"),
        pytest.param({"webserver-timeout": 5}, 5, id="timeout=5"),
        pytest.param({"webserver-timeout": 3}, 3, id="timeout=3"),
    ],
    indirect=["update_config"],
)
@pytest.mark.usefixtures("update_config")
def test_django_webserver_timeout(django_app: App, juju: jubilant.Juju, timeout):
    """
    arrange: build and deploy the django charm, and change the gunicorn timeout configuration.
    act: send long-running requests to the django application managed by the django charm.
    assert: the gunicorn should restart the worker if the request duration exceeds the timeout.
    """
    safety_timeout = timeout + 3
    status = juju.status()
    for unit in status.apps[django_app.name].units.values():
        assert requests.get(
            f"http://{unit.address}:8000/sleep?duration={timeout - 1}", timeout=safety_timeout
        ).ok
        assert not requests.get(
            f"http://{unit.address}:8000/sleep?duration={timeout + 1}", timeout=safety_timeout
        )


def test_django_database_migration(django_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the django charm with database migration enabled.
    act: access an endpoint requiring database.
    assert: request succeed.
    """
    status = juju.status()
    for unit in status.apps[django_app.name].units.values():
        assert requests.get(f"http://{unit.address}:8000/len/users", timeout=1).ok


@pytest.mark.parametrize(
    "update_config, expected_settings",
    [
        pytest.param(
            {"django-allowed-hosts": "test"},
            {"ALLOWED_HOSTS": ["test", "django-k8s.testing"]},
            id="allowed-host",
        ),
        pytest.param({"django-secret-key": "test"}, {"SECRET_KEY": "test"}, id="secret-key"),
    ],
    indirect=["update_config"],
)
@pytest.mark.usefixtures("update_config")
def test_django_charm_config(django_app: App, juju: jubilant.Juju, expected_settings):
    """
    arrange: build and deploy the django charm, and change the django related configuration.
    act: send request to the django application to retrieve the corresponding settings.
    assert: settings in django application correctly updated according to the charm configuration.
    """
    status = juju.status()
    for unit in status.apps[django_app.name].units.values():
        for setting, value in expected_settings.items():
            url = f"http://{unit.address}:8000/settings/{setting}"
            # it is necessary to specify a host header if the IP or '*' is not in ALLOWED_HOSTS
            assert (
                value
                == requests.get(url, headers={"Host": "django-k8s.testing"}, timeout=5).json()
            )


def test_django_create_superuser(django_app: App, juju: jubilant.Juju):
    """
    arrange: build and deploy the django charm.
    act: create a superuser using the create-superuser action.
    assert: a superuser is created by the charm.
    """
    status = juju.status()
    unit_name = list(status.apps[django_app.name].units.keys())[0]

    task = juju.run(
        unit_name, "create-superuser", {"email": "test@example.com", "username": "test"}
    )
    password = task.results["password"]

    for unit in status.apps[django_app.name].units.values():
        assert requests.get(
            f"http://{unit.address}:8000/login",
            params={"username": "test", "password": password},
            timeout=1,
        ).ok
