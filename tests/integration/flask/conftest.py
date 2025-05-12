# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for flask charm integration tests."""

import os
import pathlib
from secrets import token_hex

import boto3
import pytest
import pytest_asyncio
from botocore.config import Config as BotoConfig
from juju.application import Application
from juju.model import Model
from pytest import Config, FixtureRequest
from pytest_operator.plugin import OpsTest

from tests.integration.helpers import inject_charm_config, inject_venv

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(autouse=True)
def cwd():
    return os.chdir(PROJECT_ROOT / "examples/flask")


@pytest.fixture(scope="module", name="test_async_flask_image")
def fixture_test_async_flask_image(pytestconfig: Config):
    """Return the --test-async-flask-image test parameter."""
    test_flask_image = pytestconfig.getoption("--test-async-flask-image")
    if not test_flask_image:
        raise ValueError("the following arguments are required: --test-async-flask-image")
    return test_flask_image


@pytest_asyncio.fixture(scope="module", name="charm_file")
async def charm_file_fixture(pytestconfig: pytest.Config, ops_test: OpsTest) -> pathlib.Path:
    """Get the existing charm file."""
    charm_file = next(
        (f for f in pytestconfig.getoption("--charm-file") if "flask-k8s" in f), None
    )
    if not charm_file:
        charm_file = await ops_test.build_charm(PROJECT_ROOT / "examples/flask")
    elif charm_file[0] != "/":
        charm_file = PROJECT_ROOT / charm_file
    inject_venv(charm_file, PROJECT_ROOT / "src" / "paas_charm")
    return pathlib.Path(charm_file).absolute()


@pytest_asyncio.fixture(scope="module", name="build_charm")
async def build_charm_fixture(charm_file: str, tmp_path_factory) -> str:
    """Build the charm and injects additional configurations into config.yaml.

    This fixture is designed to simulate a feature that is not yet available in charmcraft that
    allows for the modification of charm configurations during the build process.
    Three additional configurations, namely foo_str, foo_int, foo_dict, foo_bool,
    and application_root will be appended to the config.yaml file.
    """
    return inject_charm_config(
        charm_file,
        {
            "foo-str": {"type": "string"},
            "foo-int": {"type": "int"},
            "foo-bool": {"type": "boolean"},
            "foo-dict": {"type": "string"},
            "application-root": {"type": "string"},
        },
        tmp_path_factory.mktemp("flask"),
    )


@pytest_asyncio.fixture(scope="module", name="flask_app")
async def flask_app_fixture(build_charm: str, model: Model, test_flask_image: str):
    """Build and deploy the flask charm."""
    app_name = "flask-k8s"

    resources = {
        "flask-app-image": test_flask_image,
    }
    app = await model.deploy(
        build_charm, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle(raise_on_blocked=True)
    return app


@pytest_asyncio.fixture(scope="module", name="flask_db_app")
async def flask_db_app_fixture(build_charm: str, model: Model, test_db_flask_image: str):
    """Build and deploy the flask charm with test-db-flask image."""
    app_name = "flask-k8s"

    resources = {
        "flask-app-image": test_db_flask_image,
    }
    app = await model.deploy(
        build_charm, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle()
    return app


@pytest_asyncio.fixture(scope="module", name="flask_async_app")
async def flask_async_app_fixture(build_charm: str, model: Model, test_async_flask_image: str):
    """Build and deploy the flask charm with test-async-flask image."""
    app_name = "flask-async-k8s"

    resources = {
        "flask-app-image": test_async_flask_image,
    }
    app = await model.deploy(
        build_charm, resources=resources, application_name=app_name, series="jammy"
    )
    await model.wait_for_idle(raise_on_blocked=True)
    return app


@pytest_asyncio.fixture(scope="module", name="traefik_app")
async def deploy_traefik_fixture(
    model: Model,
    flask_app,  # pylint: disable=unused-argument
    traefik_app_name: str,
    external_hostname: str,
):
    """Deploy traefik."""
    app = await model.deploy(
        "traefik-k8s",
        application_name=traefik_app_name,
        channel="edge",
        trust=True,
        config={
            "external_hostname": external_hostname,
            "routing_mode": "subdomain",
        },
    )
    await model.wait_for_idle(raise_on_blocked=True)

    return app


@pytest_asyncio.fixture(scope="module", name="loki_app")
async def deploy_loki_fixture(
    model: Model,
    loki_app_name: str,
):
    """Deploy loki."""
    app = await model.deploy(
        "loki-k8s", application_name=loki_app_name, channel="latest/stable", trust=True
    )
    await model.wait_for_idle(raise_on_blocked=True)

    return app


@pytest_asyncio.fixture(scope="module", name="cos_apps")
async def deploy_cos_fixture(
    model: Model,
    loki_app,  # pylint: disable=unused-argument
    prometheus_app,  # pylint: disable=unused-argument
    grafana_app_name: str,
):
    """Deploy the cos applications."""
    cos_apps = await model.deploy(
        "grafana-k8s",
        application_name=grafana_app_name,
        channel="1.0/stable",
        revision=82,
        series="focal",
        trust=True,
    )
    await model.wait_for_idle(status="active")
    return cos_apps


@pytest_asyncio.fixture
async def update_config(model: Model, request: FixtureRequest, flask_app: Application):
    """Update the flask application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    orig_config = {k: v.get("value") for k, v in (await flask_app.get_config()).items()}
    request_config = {k: str(v) for k, v in request.param.items()}
    await flask_app.set_config(request_config)
    await model.wait_for_idle(apps=[flask_app.name])

    yield request_config

    await flask_app.set_config(
        {k: v for k, v in orig_config.items() if k in request_config and v is not None}
    )
    await flask_app.reset_config([k for k in request_config if orig_config[k] is None])
    await model.wait_for_idle(apps=[flask_app.name])


@pytest_asyncio.fixture
async def update_secret_config(model: Model, request: FixtureRequest, flask_app: Application):
    """Update a secret flask application configuration.

    This fixture must be parameterized with changing charm configurations.
    """
    orig_config = {k: v.get("value") for k, v in (await flask_app.get_config()).items()}
    request_config = {}
    for secret_config_option, secret_value in request.param.items():
        secret_id = await model.add_secret(
            secret_config_option, [f"{k}={v}" for k, v in secret_value.items()]
        )
        await model.grant_secret(secret_config_option, flask_app.name)
        request_config[secret_config_option] = secret_id
    await flask_app.set_config(request_config)
    await model.wait_for_idle(apps=[flask_app.name])

    yield request_config

    await flask_app.set_config(
        {k: v for k, v in orig_config.items() if k in request_config and v is not None}
    )
    await flask_app.reset_config([k for k in request_config if orig_config[k] is None])
    for secret_name in request_config:
        await model.remove_secret(secret_name)
    await model.wait_for_idle(apps=[flask_app.name])


@pytest.fixture(scope="module", name="localstack_address")
def localstack_address_fixture(pytestconfig: Config):
    """Provides localstack IP address to be used in the integration test."""
    address = pytestconfig.getoption("--localstack-address")
    if not address:
        raise ValueError("--localstack-address argument is required for selected test cases")
    yield address


@pytest.fixture(scope="function", name="s3_configuration")
def s3_configuration_fixture(localstack_address: str) -> dict:
    """Return the S3 configuration to use for media

    Returns:
        The S3 configuration as a dict
    """
    return {
        "endpoint": f"http://{localstack_address}:4566",
        "bucket": "paas-bucket",
        "path": "/path",
        "region": "us-east-1",
        "s3-uri-style": "path",
    }


@pytest.fixture(scope="module", name="s3_credentials")
def s3_credentials_fixture(localstack_address: str) -> dict:
    """Return the S3 credentials

    Returns:
        The S3 credentials as a dict
    """
    return {
        "access-key": token_hex(16),
        "secret-key": token_hex(16),
    }


@pytest.fixture(scope="function", name="boto_s3_client")
def boto_s3_client_fixture(model: Model, s3_configuration: dict, s3_credentials: dict):
    """Return a S3 boto3 client ready to use

    Returns:
        The boto S3 client
    """
    s3_client_config = BotoConfig(
        region_name=s3_configuration["region"],
        s3={
            "addressing_style": "virtual",
        },
        # no_proxy env variable is not read by boto3, so
        # this is needed for the tests to avoid hitting the proxy.
        proxies={},
    )

    s3_client = boto3.client(
        "s3",
        s3_configuration["region"],
        aws_access_key_id=s3_credentials["access-key"],
        aws_secret_access_key=s3_credentials["secret-key"],
        endpoint_url=s3_configuration["endpoint"],
        use_ssl=False,
        config=s3_client_config,
    )
    yield s3_client


@pytest_asyncio.fixture(scope="function", name="rabbitmq_server_integration")
async def rabbitmq_server_integration_fixture(
    ops_test_lxd: OpsTest,
    flask_app: Application,
    rabbitmq_server_app: Application,
    model: Model,
    lxd_model: Model,
):
    """Integrates flask with rabbitmq-server."""
    lxd_controller = await lxd_model.get_controller()
    lxd_username = lxd_controller.get_current_username()
    lxd_controller_name = ops_test_lxd.controller_name
    lxd_model_name = lxd_model.name
    offer_name = rabbitmq_server_app.name
    rabbitmq_offer_url = f"{lxd_controller_name}:{lxd_username}/{lxd_model_name}.{offer_name}"

    integration = await model.integrate(rabbitmq_offer_url, flask_app.name)
    await lxd_model.wait_for_idle(status="active")
    await model.wait_for_idle(apps=[flask_app.name], status="active")

    yield integration

    res = await flask_app.destroy_relation("rabbitmq", f"{rabbitmq_server_app.name}:amqp")
    await lxd_model.wait_for_idle(status="active")
    await model.wait_for_idle(apps=[flask_app.name], status="active")


@pytest_asyncio.fixture(scope="function", name="rabbitmq_k8s_integration")
async def rabbitmq_k8s_integration_fixture(
    model: Model,
    rabbitmq_k8s_app: Application,
    flask_app: Application,
):
    """Integrates flask with rabbitmq-k8s."""
    integration = await model.integrate(rabbitmq_k8s_app.name, flask_app.name)
    await model.wait_for_idle(apps=[flask_app.name, rabbitmq_k8s_app.name], status="active")

    yield integration

    await flask_app.destroy_relation("rabbitmq", f"{rabbitmq_k8s_app.name}:amqp")
    await model.wait_for_idle(apps=[flask_app.name, rabbitmq_k8s_app.name], status="active")
