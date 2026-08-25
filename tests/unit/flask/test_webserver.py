# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm Scenario tests for Gunicorn webserver behavior."""

import dataclasses
import signal
import textwrap
from unittest import mock

import ops
import pytest
from ops import pebble, testing

from paas_charm.paas_config import LoggingFormat, PaasConfig
from paas_charm.utils import enable_pebble_log_forwarding

GUNICORN_CONFIG_TEST_PARAMS = [
    pytest.param(
        {"webserver-workers": 10},
        False,
        textwrap.dedent("""\
                bind = ['0.0.0.0:8000']
                chdir = '/flask/app'
                accesslog = '/var/log/flask/access.log'
                errorlog = '/var/log/flask/error.log'
                statsd_host = 'localhost:9125'
                workers = 10"""),
        id="workers=10",
    ),
    pytest.param(
        {
            "webserver-threads": 2,
            "webserver-timeout": 3,
            "webserver-keepalive": 4,
        },
        False,
        textwrap.dedent("""\
                bind = ['0.0.0.0:8000']
                chdir = '/flask/app'
                accesslog = '/var/log/flask/access.log'
                errorlog = '/var/log/flask/error.log'
                statsd_host = 'localhost:9125'
                threads = 2
                keepalive = 4
                timeout = 3"""),
        id="threads=2,timeout=3,keepalive=4",
    ),
    pytest.param(
        {},
        True,
        textwrap.dedent("""\
                from opentelemetry import trace
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                bind = ['0.0.0.0:8000']
                chdir = '/flask/app'
                accesslog = '/var/log/flask/access.log'
                errorlog = '/var/log/flask/error.log'
                statsd_host = 'localhost:9125'
                access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %({x-request-id}o)s'


                def post_fork(server, worker):
                    trace.set_tracer_provider(TracerProvider())
                    span_processor = BatchSpanProcessor(OTLPSpanExporter())
                    trace.get_tracer_provider().add_span_processor(span_processor)
                """),
        id="with-tracing",
    ),
]


@pytest.mark.parametrize(
    "flask_context",
    [
        {
            "paas_config": PaasConfig(framework_logging_format=LoggingFormat.NONE),
            "juju_version": "3.3.1",
        }
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    "config,tracing_enabled,expected_config",
    GUNICORN_CONFIG_TEST_PARAMS,
)
def test_gunicorn_config(
    flask_context,
    base_state,
    container_name: str,
    config: dict,
    tracing_enabled: bool,
    expected_config: str,
) -> None:
    """
    arrange: configure Gunicorn and optionally relate tracing.
    act: reconcile the charm.
    assert: the exact generated config and config-check exec arguments are preserved.
    """
    if tracing_enabled:
        base_state["relations"].append(
            testing.Relation(
                endpoint="tracing",
                interface="tracing",
                remote_app_data={
                    "receivers": (
                        '[{"protocol": {"name": "otlp_http", "type": "http"}, '
                        '"url": "http://test-ip:4318"}]'
                    )
                },
            )
        )
    state = testing.State(**{**base_state, "config": config})

    out = flask_context.run(flask_context.on.config_changed(), state)

    filesystem = out.get_container(container_name).get_filesystem(flask_context)
    assert (filesystem / "flask" / "gunicorn.conf.py").read_text() == expected_config
    check_exec = next(
        args
        for args in flask_context.exec_history[container_name]
        if args.command[-1] == "--check-config"
    )
    assert check_exec.command == [
        "/bin/python3",
        "-m",
        "gunicorn",
        "-c",
        "/flask/gunicorn.conf.py",
        "app:app",
        "-k",
        "sync",
        "--check-config",
    ]
    assert check_exec.working_dir == "/flask/app"
    assert check_exec.user == check_exec.group == "_daemon_"
    assert check_exec.environment["FLASK_SECRET_KEY"] == "test"


def test_real_paas_config_enables_structured_logging(
    flask_context,
    base_state,
    container_name: str,
) -> None:
    """
    arrange: use the real Flask paas-config with JSON framework logging.
    act: reconcile the charm.
    assert: the generated Gunicorn config installs the structured logger and middleware.
    """
    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    filesystem = out.get_container(container_name).get_filesystem(flask_context)
    config = (filesystem / "flask" / "gunicorn.conf.py").read_text()
    assert "class GunicornJsonFormatter(logging.Formatter):" in config
    assert "class GunicornJsonLogger(glogging.Logger):" in config
    assert "logger_class = GunicornJsonLogger" in config
    assert "worker.app.wsgi = _patched_wsgi" in config


@pytest.mark.parametrize("is_running", [True, False])
def test_webserver_reload(
    flask_context,
    base_state,
    is_running: bool,
) -> None:
    """
    arrange: set the Flask service running state and leave its config absent.
    act: reconcile the charm so the generated config changes.
    assert: a SIGHUP is sent only to a running Gunicorn service.
    """
    container = dataclasses.replace(
        next(iter(base_state["containers"])),
        service_statuses={
            "flask": (pebble.ServiceStatus.ACTIVE if is_running else pebble.ServiceStatus.INACTIVE)
        },
    )
    state = testing.State(**{**base_state, "containers": {container}})

    with mock.patch.object(ops.Container, "send_signal") as send_signal:
        out = flask_context.run(flask_context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus()
    assert send_signal.call_count == (1 if is_running else 0)
    if is_running:
        assert send_signal.call_args.args == (signal.SIGHUP, "flask")


def test_enable_pebble_log_forwarding(monkeypatch) -> None:
    """
    arrange: set Juju versions around the Pebble forwarding support boundary.
    act: query Pebble log-forwarding support.
    assert: forwarding is enabled from Juju 3.4.
    """
    monkeypatch.setenv("JUJU_VERSION", "3.3.1")
    assert not enable_pebble_log_forwarding()
    monkeypatch.setenv("JUJU_VERSION", "3.4.0")
    assert enable_pebble_log_forwarding()


@pytest.mark.parametrize(
    "flask_context",
    [
        {
            "paas_config": PaasConfig(framework_logging_format=LoggingFormat.NONE),
            "juju_version": "3.4.0",
        }
    ],
    indirect=True,
)
def test_gunicorn_config_with_pebble_log_forwarding(
    flask_context,
    base_state,
    container_name: str,
) -> None:
    """
    arrange: run the charm on a Juju version supporting Pebble log forwarding.
    act: reconcile the charm.
    assert: generated access and error logs target standard streams.
    """
    out = flask_context.run(
        flask_context.on.config_changed(),
        testing.State(**base_state),
    )

    filesystem = out.get_container(container_name).get_filesystem(flask_context)
    config = (filesystem / "flask" / "gunicorn.conf.py").read_text()
    assert "accesslog = '-'" in config
    assert "errorlog = '-'" in config
