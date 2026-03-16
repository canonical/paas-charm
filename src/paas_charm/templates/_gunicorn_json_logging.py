# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared Gunicorn JSON logging snippet included by gunicorn.conf.py.j2."""

import json
import logging
import time
from contextvars import ContextVar
from typing import Any

from gunicorn import glogging

_span_context_var: ContextVar[dict[str, str]] = ContextVar("_span_context_var", default={})

_SEVERITY_MAP = {
    "WARNING": "WARN",
    "CRITICAL": "FATAL",
}


class OtelSpanMiddleware:
    """WSGI middleware that captures OTEL span context before the span ends.

    Wraps start_response so that span IDs are saved to a ContextVar while the
    OTEL instrumentation span is still live (it ends after start_response returns
    in FlaskInstrumentor/DjangoInstrumentor, before Gunicorn calls access()).
    """

    def __init__(self, app: Any) -> None:
        """Store the wrapped WSGI app."""
        self.app = app

    def __call__(self, environ: Any, start_response: Any) -> Any:
        """Wrap start_response and persist active span IDs in context."""
        _span_context_var.set({})

        def capturing_start_response(status: Any, headers: Any, exc_info: Any = None) -> Any:
            """Capture trace/span IDs while the instrumented request span is still live."""
            try:
                from opentelemetry import trace  # type: ignore[import-not-found]

                span = trace.get_current_span()
                ctx = span.get_span_context()
                if ctx and ctx.is_valid:
                    _span_context_var.set(
                        {
                            "traceId": format(ctx.trace_id, "032x"),
                            "spanId": format(ctx.span_id, "016x"),
                        }
                    )
                else:
                    _span_context_var.set({})
            except ImportError:
                pass
            return start_response(status, headers, exc_info)

        return self.app(environ, capturing_start_response)


class GunicornJsonFormatter(logging.Formatter):
    """JSON formatter for Gunicorn error/warning/info log records."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record as structured JSON."""
        ids = _span_context_var.get()
        payload: dict[str, Any] = {
            "timestamp": _iso_timestamp(record.created),
            "severityText": _SEVERITY_MAP.get(record.levelname, record.levelname),
            "body": record.getMessage(),
        }
        payload.update(ids)
        attributes: dict[str, Any] = {"logger.name": record.name}
        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            if exc_type is not None:
                attributes["exception.type"] = exc_type.__qualname__
            if exc_value is not None:
                attributes["exception.message"] = str(exc_value)
            attributes["exception.stacktrace"] = self.formatException(record.exc_info)
        payload["attributes"] = attributes
        return json.dumps(payload, default=str)


class GunicornJsonLogger(glogging.Logger):
    """Gunicorn logger class that emits structured JSON logs."""

    def setup(self, cfg: Any) -> None:
        """Initialize logger handlers and apply the JSON formatter."""
        super().setup(cfg)
        formatter = GunicornJsonFormatter()
        for handler in self.error_log.handlers:
            handler.setFormatter(formatter)

    def access(self, resp: Any, req: Any, environ: Any, request_time: Any) -> None:
        """Emit a structured JSON access log entry."""
        ids = _span_context_var.get()
        status_str = resp.status
        try:
            status_code = int(status_str.split(" ", 1)[0])
        except (ValueError, AttributeError):
            status_code = status_str
        path = environ.get("PATH_INFO", "")
        query = environ.get("QUERY_STRING", "")
        method = environ.get("REQUEST_METHOD", "")
        client = environ.get("REMOTE_ADDR", "")
        duration_ms = request_time.seconds * 1000 + request_time.microseconds / 1000
        body = (
            f'{client} - "{method} {path} {environ.get("SERVER_PROTOCOL", "")}" {status_code}'
        )
        try:
            if self.cfg.access_log_format is not None:
                safe_atoms = self.atoms_wrapper_class(self.atoms(resp, req, environ, request_time))
                body = self.cfg.access_log_format % safe_atoms
        except (TypeError, ValueError, KeyError):
            pass
        payload: dict[str, Any] = {
            "timestamp": _iso_timestamp(time.time()),
            "severityText": "INFO",
            "body": body,
        }
        payload.update(ids)
        attributes: dict[str, Any] = {
            "logger.name": "gunicorn.access",
            "http.request.method": method,
            "url.path": path,
            "http.response.status_code": status_code,
            "duration_ms": round(duration_ms, 3),
        }
        if query:
            attributes["url.query"] = query
        if client:
            attributes["client.address"] = client
        x_request_id = environ.get("HTTP_X_REQUEST_ID")
        if x_request_id:
            attributes["http.request.header.x-request-id"] = x_request_id
        payload["attributes"] = attributes
        if self.cfg.accesslog:
            self.access_log.info(json.dumps(payload, default=str))


def _iso_timestamp(epoch: float) -> str:
    """Convert epoch seconds to RFC3339 timestamp with millisecond precision."""
    millis = int((epoch % 1) * 1000)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(epoch)) + f".{millis:03d}Z"
