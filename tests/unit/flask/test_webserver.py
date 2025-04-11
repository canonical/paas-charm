# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm unit tests for the webserver module."""

# this is a unit test file
# pylint: disable=protected-access

import textwrap
import unittest.mock

import ops
import pytest
from ops.testing import Harness

from paas_charm._gunicorn.webserver import GunicornWebserver, WebserverConfig
from paas_charm._gunicorn.workload_config import create_workload_config
from paas_charm._gunicorn.wsgi_app import WsgiApp
from paas_charm.charm_state import CharmState
from paas_charm.utils import enable_pebble_log_forwarding

from .constants import DEFAULT_LAYER, FLASK_CONTAINER_NAME

GUNICORN_CONFIG_TEST_PARAMS = [
    pytest.param(
        {"workers": 10},
        False,
        textwrap.dedent(
            """\
                bind = ['0.0.0.0:8000']
                chdir = '/flask/app'
                accesslog = '/var/log/flask/access.log'
                errorlog = '/var/log/flask/error.log'
                statsd_host = 'localhost:9125'
                workers = 10"""
        ),
        id="workers=10",
    ),
    pytest.param(
        {"threads": 2, "timeout": 3, "keepalive": 4},
        False,
        textwrap.dedent(
            """\
                bind = ['0.0.0.0:8000']
                chdir = '/flask/app'
                accesslog = '/var/log/flask/access.log'
                errorlog = '/var/log/flask/error.log'
                statsd_host = 'localhost:9125'
                threads = 2
                keepalive = 4
                timeout = 3"""
        ),
        id="threads=2,timeout=3,keepalive=4",
    ),
    pytest.param(
        {},
        True,
        textwrap.dedent(
            """\
                from opentelemetry import trace
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                bind = ['0.0.0.0:8000']
                chdir = '/flask/app'
                accesslog = '/var/log/flask/access.log'
                errorlog = '/var/log/flask/error.log'
                statsd_host = 'localhost:9125'


                def post_fork(server, worker):
                    trace.set_tracer_provider(TracerProvider())
                    span_processor = BatchSpanProcessor(OTLPSpanExporter())
                    trace.get_tracer_provider().add_span_processor(span_processor)
                """
        ),
        id="with-tracing",
    ),
]


@pytest.mark.parametrize(
    "charm_state_params, tracing_enabled, config_file", GUNICORN_CONFIG_TEST_PARAMS
)
def test_gunicorn_config(
    harness: Harness,
    charm_state_params,
    tracing_enabled,
    config_file,
    database_migration_mock,
) -> None:
    """
    arrange: create the Gunicorn webserver object with a controlled charm state generated by the
        charm_state_params parameter.
    act: invoke the update_config method of the webserver object.
    assert: gunicorn configuration file inside the flask app container should change accordingly.
    """
    harness.begin()
    container: ops.Container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    harness.set_can_connect(FLASK_CONTAINER_NAME, True)
    container.add_layer("default", DEFAULT_LAYER)

    charm_state = CharmState(
        framework="flask",
        secret_key="",
        is_secret_storage_ready=True,
    )
    workload_config = create_workload_config(
        framework_name="flask",
        unit_name="flask/0",
        state_dir=harness.charm._state_dir,
        tracing_enabled=tracing_enabled,
    )
    webserver_config = WebserverConfig(**charm_state_params)
    webserver = GunicornWebserver(
        webserver_config=webserver_config,
        workload_config=workload_config,
        container=container,
    )
    flask_app = WsgiApp(
        container=container,
        charm_state=charm_state,
        workload_config=workload_config,
        webserver=webserver,
        database_migration=database_migration_mock,
    )
    flask_app.restart()
    webserver.update_config(
        is_webserver_running=False,
        environment=flask_app.gen_environment(),
        command=DEFAULT_LAYER["services"]["flask"]["command"],
    )

    assert container.pull("/flask/gunicorn.conf.py").read() == config_file


@pytest.mark.parametrize("is_running", [True, False])
def test_webserver_reload(monkeypatch, harness: Harness, is_running, database_migration_mock):
    """
    arrange: put an empty file in the Flask container and create a webserver object with default
        charm state.
    act: run the update_config method of the webserver object with different server running status.
    assert: webserver object should send signal to the Gunicorn server based on the running status.
    """
    harness.begin()
    container: ops.Container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    harness.set_can_connect(container, True)
    container.add_layer("default", DEFAULT_LAYER)

    container.push("/flask/gunicorn.conf.py", "")
    charm_state = CharmState(
        framework="flask",
        secret_key="",
        is_secret_storage_ready=True,
    )
    webserver_config = WebserverConfig()
    workload_config = create_workload_config(
        framework_name="flask", unit_name="flask/0", state_dir=harness.charm._state_dir
    )
    webserver = GunicornWebserver(
        webserver_config=webserver_config,
        workload_config=workload_config,
        container=container,
    )
    flask_app = WsgiApp(
        container=container,
        charm_state=charm_state,
        workload_config=workload_config,
        webserver=webserver,
        database_migration=database_migration_mock,
    )
    flask_app.restart()
    send_signal_mock = unittest.mock.MagicMock()
    monkeypatch.setattr(container, "send_signal", send_signal_mock)
    webserver.update_config(
        is_webserver_running=is_running,
        environment=flask_app.gen_environment(),
        command=DEFAULT_LAYER["services"]["flask"]["command"],
    )
    assert send_signal_mock.call_count == (1 if is_running else 0)


def test_enable_pebble_log_forwarding(monkeypatch):
    """
    arrange: set JUJU_VERSION environment variable to different versions.
    act: call the enable_pebble_log_forwarding function.
    assert: enable_pebble_log_forwarding should return True when pebble log forwarding is supported
        in the given juju version.
    """
    monkeypatch.setenv("JUJU_VERSION", "3.3.1")
    assert not enable_pebble_log_forwarding()
    monkeypatch.setenv("JUJU_VERSION", "3.4.0")
    assert enable_pebble_log_forwarding()


def test_gunicorn_config_with_pebble_log_forwarding(
    monkeypatch, harness: Harness, database_migration_mock
):
    """
    arrange: set JUJU_VERSION environment variable to a version supporting pebble log forwarding.
    act: generate the gunicorn configuration file.
    assert: access logs and error logs should be sent to standard IO in the configuration.
    """
    monkeypatch.setenv("JUJU_VERSION", "3.4.0")
    harness.begin()
    container: ops.Container = harness.model.unit.get_container(FLASK_CONTAINER_NAME)
    harness.set_can_connect(FLASK_CONTAINER_NAME, True)
    container.add_layer("default", DEFAULT_LAYER)
    charm_state = CharmState(
        framework="flask",
        secret_key="",
        is_secret_storage_ready=True,
    )
    workload_config = create_workload_config(
        framework_name="flask", unit_name="flask/0", state_dir=harness.charm._state_dir
    )
    webserver_config = WebserverConfig()
    webserver = GunicornWebserver(
        webserver_config=webserver_config,
        workload_config=workload_config,
        container=container,
    )
    flask_app = WsgiApp(
        container=container,
        charm_state=charm_state,
        workload_config=workload_config,
        webserver=webserver,
        database_migration=database_migration_mock,
    )
    flask_app.restart()
    webserver.update_config(
        is_webserver_running=False,
        environment=flask_app.gen_environment(),
        command=DEFAULT_LAYER["services"]["flask"]["command"],
    )
    config = container.pull("/flask/gunicorn.conf.py").read()
    assert "accesslog = '-'" in config
    assert "errorlog = '-'" in config
