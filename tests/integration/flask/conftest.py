# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import os
import pathlib

import jubilant
import pytest

from tests.integration.conftest import build_charm_file, inject_charm_config
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/flask/charm")


@pytest.fixture(scope="module", name="flask_db_app")
def flask_db_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    tmp_path_factory,
):
    """Build and deploy the flask charm with test-db-flask image."""
    framework = "flask"
    app_name = f"{framework}-k8s"

    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return App(app_name)

    # Build the charm with additional config options
    charm_file = build_charm_file(pytestconfig, framework, tmp_path_factory)
    charm_file = inject_charm_config(
        charm_file,
        {
            "config": {
                "options": {
                    "foo-str": {"type": "string"},
                    "foo-int": {"type": "int"},
                    "foo-bool": {"type": "boolean"},
                    "foo-dict": {"type": "string"},
                    "application-root": {"type": "string"},
                }
            }
        },
        tmp_path_factory.mktemp("flask"),
    )

    resources = {
        "flask-app-image": pytestconfig.getoption("--test-db-flask-image"),
    }

    try:
        juju.deploy(
            charm=charm_file,
            app=app_name,
            resources=resources,
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: status.apps[app_name].is_active, timeout=10 * 60)
    return App(app_name)


@pytest.fixture(scope="module", name="flask_async_app")
def flask_async_app_fixture(
    juju: jubilant.Juju,
    pytestconfig: pytest.Config,
    tmp_path_factory,
):
    """Build and deploy the flask charm with test-async-flask image."""
    framework = "flask"
    app_name = "flask-async-k8s"

    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return App(app_name)

    # Build the charm with additional config options
    charm_file = build_charm_file(pytestconfig, framework, tmp_path_factory)
    charm_file = inject_charm_config(
        charm_file,
        {
            "config": {
                "options": {
                    "foo-str": {"type": "string"},
                    "foo-int": {"type": "int"},
                    "foo-bool": {"type": "boolean"},
                    "foo-dict": {"type": "string"},
                    "application-root": {"type": "string"},
                }
            }
        },
        tmp_path_factory.mktemp("flask"),
    )

    resources = {
        "flask-app-image": pytestconfig.getoption("--test-async-flask-image"),
    }

    try:
        juju.deploy(
            charm=charm_file,
            app=app_name,
            resources=resources,
        )
    except jubilant.CLIError as err:
        if "application already exists" not in err.stderr:
            raise err

    juju.wait(lambda status: status.apps[app_name].is_active, timeout=10 * 60)
    return App(app_name)


@pytest.fixture(scope="module", name="traefik_app")
def deploy_traefik_fixture(
    juju: jubilant.Juju,
    flask_app: App,  # pylint: disable=unused-argument
    traefik_app_name: str,
    external_hostname: str,
):
    """Deploy traefik."""
    if not juju.status().apps.get(traefik_app_name):
        juju.deploy(
            traefik_app_name,
            channel="edge",
            trust=True,
            config={
                "external_hostname": external_hostname,
                "routing_mode": "subdomain",
            },
        )
    juju.wait(
        lambda status: status.apps[traefik_app_name].is_active,
        error=jubilant.any_blocked,
    )
    return App(traefik_app_name)


@pytest.fixture
def update_config(juju: jubilant.Juju, request: pytest.FixtureRequest, flask_app: App):
    """Update the flask application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    app_name = flask_app.name
    orig_config = juju.config(app_name)

    request_config = {k: str(v) for k, v in request.param.items()}
    juju.config(app_name, request_config)
    juju.wait(lambda status: status.apps[app_name].is_active or status.apps[app_name].is_blocked)

    yield request_config

    # Restore original configuration
    restore_config = {k: str(v) for k, v in orig_config.items() if k in request_config}
    reset_config = [k for k in request_config if orig_config.get(k) is None]
    juju.config(app_name, restore_config, reset=reset_config)


@pytest.fixture
def update_secret_config(juju: jubilant.Juju, request: pytest.FixtureRequest, flask_app: App):
    """Update a secret flask application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    app_name = flask_app.name
    orig_config = juju.config(app_name)
    request_config = {}
    secret_ids = []

    for secret_config_option, secret_value in request.param.items():
        secret_id = juju.add_secret(secret_config_option, secret_value)

        juju.grant_secret(secret_id, app_name)
        request_config[secret_config_option] = secret_id
        secret_ids.append(secret_id)

    juju.config(app_name, request_config)
    juju.wait(lambda status: status.apps[app_name].is_active)

    yield request_config

    # Restore original configuration
    restore_config = {k: str(v) for k, v in orig_config.items() if k in request_config}
    reset_config = [k for k in request_config if orig_config.get(k) is None]
    juju.config(app_name, restore_config, reset=reset_config)

    for secret_id in secret_ids:
        juju.remove_secret(secret_id)
