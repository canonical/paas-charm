# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Gunicorn JSON logging (GunicornJsonLogger, GunicornJsonFormatter).

The logger classes are defined inline in the gunicorn.conf.py.j2 Jinja2 template.
Tests render the template with enable_json_logging=True, exec() the output to
obtain the classes, then exercise them directly — no Juju/charm machinery needed.
"""

import datetime
import io
import json
import pathlib

import jinja2
import pytest

# pylint: disable=attribute-defined-outside-init

_TEMPLATES_DIR = (
    pathlib.Path(__file__).parent.parent.parent.parent / "src" / "paas_charm" / "templates"
)


def _render_template(enable_tracing: bool = False, enable_json_logging: bool = True) -> dict:
    """Render gunicorn.conf.py.j2 and exec() the result.

    Returns the namespace dict produced by exec().
    """
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)
    rendered = env.get_template("gunicorn.conf.py.j2").render(
        workload_port=8000,
        workload_app_dir="/flask/app",
        access_log="-",
        error_log="-",
        statsd_host="localhost:9125",
        enable_tracing=enable_tracing,
        enable_json_logging=enable_json_logging,
        config_entries={},
    )
    ns: dict = {}
    exec(rendered, ns)  # nosec: B102  # pylint: disable=exec-used
    return ns


class FakeCfg:  # pylint: disable=too-few-public-methods
    """Minimal Gunicorn config stub for logger construction."""

    accesslog = "-"
    loglevel = "info"
    access_log_format = ""
    logconfig = None
    logconfig_dict = None
    logconfig_json = None
    syslog = False
    syslog_facility = "user"
    syslog_prefix = "gunicorn"
    syslog_addr = "udp://localhost:514"
    errorlog = "-"
    capture_output = False
    disable_redirect_access_to_syslog = False


class FakeResp:  # pylint: disable=too-few-public-methods
    """Minimal Gunicorn response stub for access() calls."""

    status = "200 OK"


@pytest.fixture(name="logger_ns")
def logger_ns_fixture():
    """Render template and return the exec namespace."""
    return _render_template()


@pytest.fixture(name="gunicorn_logger")
def gunicorn_logger_fixture(logger_ns):
    """Return a configured GunicornJsonLogger instance."""
    return logger_ns["GunicornJsonLogger"](FakeCfg())


def test_error_log_otel_fields(gunicorn_logger):
    """
    arrange: configure GunicornJsonLogger with no active OTEL span.
    act: emit an error log via logger.error().
    assert: output is valid JSON with expected OTEL top-level fields.
    """
    buf = io.StringIO()
    gunicorn_logger.error_log.handlers[0].stream = buf

    gunicorn_logger.error("something went wrong")

    parsed = json.loads(buf.getvalue().strip())
    for field in ("timestamp", "severityText", "body", "attributes"):
        assert field in parsed, f"OTEL field {field!r} missing from error log: {parsed}"
    assert parsed["severityText"] == "ERROR"
    assert parsed["body"] == "something went wrong"
    assert parsed["attributes"]["logger.name"] == "gunicorn.error"


def test_error_log_exception_fields(gunicorn_logger):
    """
    arrange: configure GunicornJsonLogger; raise an exception to attach exc_info.
    act: emit an error log with exc_info=True.
    assert: exception.type, exception.message, exception.stacktrace are in attributes.
    """
    buf = io.StringIO()
    gunicorn_logger.error_log.handlers[0].stream = buf

    try:
        raise RuntimeError("intentional test error")
    except RuntimeError:
        gunicorn_logger.error("handler failed", exc_info=True)

    parsed = json.loads(buf.getvalue().strip())
    attrs = parsed["attributes"]
    assert attrs.get("exception.type") == "RuntimeError"
    assert attrs.get("exception.message") == "intentional test error"
    assert "exception.stacktrace" in attrs


def test_access_log_otel_fields(gunicorn_logger):
    """
    arrange: configure GunicornJsonLogger with a simulated GET request.
    act: call access() with a fake response and environ.
    assert: output is valid JSON with expected OTEL fields and HTTP attributes.
    """
    buf = io.StringIO()
    gunicorn_logger.access_log.handlers[0].stream = buf

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/hello",
        "QUERY_STRING": "",
        "REMOTE_ADDR": "192.168.1.1",
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    gunicorn_logger.access(FakeResp(), None, environ, datetime.timedelta(milliseconds=10))

    parsed = json.loads(buf.getvalue().strip())
    for field in ("timestamp", "severityText", "body", "attributes"):
        assert field in parsed, f"OTEL field {field!r} missing from access log: {parsed}"
    attrs = parsed["attributes"]
    assert attrs["logger.name"] == "gunicorn.access"
    assert attrs["http.request.method"] == "GET"
    assert attrs["url.path"] == "/hello"
    assert attrs["http.response.status_code"] == 200
    assert "url.query" not in attrs, "url.query should be absent when QUERY_STRING is empty"


def test_access_log_query_string(gunicorn_logger):
    """
    arrange: configure GunicornJsonLogger; environ includes a non-empty QUERY_STRING.
    act: call access().
    assert: url.query is present in attributes.
    """
    buf = io.StringIO()
    gunicorn_logger.access_log.handlers[0].stream = buf

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/search",
        "QUERY_STRING": "q=hello&page=2",
        "REMOTE_ADDR": "10.0.0.1",
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    gunicorn_logger.access(FakeResp(), None, environ, datetime.timedelta(milliseconds=5))

    parsed = json.loads(buf.getvalue().strip())
    assert parsed["attributes"]["url.query"] == "q=hello&page=2"


def test_access_log_body_uses_gunicorn_format(gunicorn_logger):
    """
    arrange: configure a custom gunicorn access_log_format.
    act: call access() with fake request values.
    assert: body follows the configured gunicorn access log format.
    """
    buf = io.StringIO()
    gunicorn_logger.access_log.handlers[0].stream = buf
    gunicorn_logger.cfg.access_log_format = "%(h)s %(s)s"

    environ = {
        "REQUEST_METHOD": "PATCH",
        "PATH_INFO": "/items/1",
        "RAW_URI": "/items/1",
        "QUERY_STRING": "",
        "REMOTE_ADDR": "10.1.1.1",
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    resp = FakeResp()
    resp.headers = {}
    gunicorn_logger.access(resp, {}, environ, datetime.timedelta(milliseconds=2))

    parsed = json.loads(buf.getvalue().strip())
    assert parsed["body"] == "10.1.1.1 200"


def test_access_log_body_falls_back_when_format_invalid(gunicorn_logger):
    """
    arrange: configure an invalid gunicorn access_log_format.
    act: call access().
    assert: body falls back to the manual safe access log message.
    """
    buf = io.StringIO()
    gunicorn_logger.access_log.handlers[0].stream = buf
    gunicorn_logger.cfg.access_log_format = "%(missing_atom)s"

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/fallback",
        "QUERY_STRING": "",
        "REMOTE_ADDR": "10.1.1.2",
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    gunicorn_logger.access(FakeResp(), None, environ, datetime.timedelta(milliseconds=2))

    parsed = json.loads(buf.getvalue().strip())
    assert parsed["body"] == '10.1.1.2 - "GET /fallback HTTP/1.1" 200'


def test_access_log_body_keeps_empty_string_format(gunicorn_logger):
    """
    arrange: configure an explicit empty gunicorn access_log_format.
    act: call access().
    assert: body keeps the formatted empty string (no fallback body is injected).
    """
    buf = io.StringIO()
    gunicorn_logger.access_log.handlers[0].stream = buf
    gunicorn_logger.cfg.access_log_format = ""

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/empty-body",
        "RAW_URI": "/empty-body",
        "QUERY_STRING": "",
        "REMOTE_ADDR": "10.1.1.3",
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    resp = FakeResp()
    resp.headers = {}
    gunicorn_logger.access(resp, {}, environ, datetime.timedelta(milliseconds=2))

    parsed = json.loads(buf.getvalue().strip())
    assert parsed["body"] == ""


def test_access_log_otel_correlation(logger_ns):
    """
    arrange: set traceId/spanId in the ContextVar (simulating OtelSpanMiddleware).
    act: call access().
    assert: traceId and spanId appear in the JSON log.
    """
    _span_context_var = logger_ns["_span_context_var"]
    gunicorn_logger = logger_ns["GunicornJsonLogger"](FakeCfg())
    buf = io.StringIO()
    gunicorn_logger.access_log.handlers[0].stream = buf

    _span_context_var.set({"traceId": "a" * 32, "spanId": "b" * 16})
    try:
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/data",
            "QUERY_STRING": "",
            "REMOTE_ADDR": "10.0.0.2",
            "SERVER_PROTOCOL": "HTTP/1.1",
        }
        gunicorn_logger.access(FakeResp(), None, environ, datetime.timedelta(milliseconds=1))
    finally:
        _span_context_var.set({})

    parsed = json.loads(buf.getvalue().strip())
    assert parsed.get("traceId") == "a" * 32
    assert parsed.get("spanId") == "b" * 16


def test_span_context_reset_between_requests(logger_ns):
    """
    arrange: stale traceId/spanId left in ContextVar from a previous request.
    act: run a new request through OtelSpanMiddleware where capturing_start_response
         is never called (simulating a dropped connection before response starts).
    assert: access() sees no traceId/spanId — stale values do not leak.
    """
    _span_context_var = logger_ns["_span_context_var"]
    otel_span_middleware = logger_ns["OtelSpanMiddleware"]
    gunicorn_logger = logger_ns["GunicornJsonLogger"](FakeCfg())
    buf = io.StringIO()
    gunicorn_logger.access_log.handlers[0].stream = buf

    _span_context_var.set({"traceId": "a" * 32, "spanId": "b" * 16})

    def wsgi_app_no_start_response(_environ, _start_response):
        return []

    middleware = otel_span_middleware(wsgi_app_no_start_response)
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/test",
        "QUERY_STRING": "",
        "REMOTE_ADDR": "10.0.0.1",
        "SERVER_PROTOCOL": "HTTP/1.1",
    }
    list(middleware(environ, lambda *a: None))

    gunicorn_logger.access(FakeResp(), None, environ, datetime.timedelta(milliseconds=1))

    parsed = json.loads(buf.getvalue().strip())
    assert "traceId" not in parsed, f"Stale traceId leaked into access log: {parsed}"
    assert "spanId" not in parsed, f"Stale spanId leaked into access log: {parsed}"


def test_no_json_logging_when_disabled():
    """
    arrange: render template with enable_json_logging=False.
    act: inspect namespace.
    assert: GunicornJsonLogger and OtelSpanMiddleware are not defined.
    """
    ns = _render_template(enable_json_logging=False)
    assert "GunicornJsonLogger" not in ns
    assert "OtelSpanMiddleware" not in ns
    assert "logger_class" not in ns
