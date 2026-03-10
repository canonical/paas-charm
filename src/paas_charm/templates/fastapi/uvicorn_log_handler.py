# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""JSON log formatter and OTEL correlation filter for Uvicorn.

This file is pushed by the charm into /tmp/fastapi/log_config/ inside the application
container and loaded by Uvicorn via the UVICORN_LOG_CONFIG environment variable.
It must only depend on the Python standard library; opentelemetry-api is used
only when already installed by the user.

Field names follow the OpenTelemetry Log Data Model and semantic conventions:
https://opentelemetry.io/docs/specs/otel/logs/data-model/
https://opentelemetry.io/docs/specs/semconv/general/logs/
"""

import json
import logging
import time
from contextvars import ContextVar
from typing import Any

# Stores the last known {traceId, spanId} for the current async context.
# Populated by OtelCorrelationFilter whenever a valid span is active (access log path).
# Read as fallback when the span has already ended (error log path).
#
# Keep-alive note: on HTTP/1.1 connections, multiple requests share the same asyncio
# task and therefore the same ContextVar.  OtelCorrelationFilter detects request
# boundaries via the "uvicorn.access" logger name: if an access log arrives with no
# active span the contextvar is cleared, preventing stale IDs from leaking into
# subsequent untraced requests.
_span_context_var: ContextVar[dict[str, str]] = ContextVar("_span_context_var", default={})

# Map Python log level names to OTEL severityText values.
_SEVERITY_MAP = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARN",
    "ERROR": "ERROR",
    "CRITICAL": "FATAL",
}


class OtelCorrelationFilter(logging.Filter):
    """Add OpenTelemetry trace/span IDs to log records.

    When a valid OTEL span is active, injects ``traceId`` and ``spanId``
    into the record and saves them to a ``ContextVar`` for later use.

    When no span is active (e.g. error logs emitted after the span has ended),
    falls back to the value saved in the ``ContextVar`` so that error logs
    emitted in the same async task are still correlated to the request.

    If opentelemetry-api is not installed at all, records are passed through
    unchanged (``traceId`` and ``spanId`` are simply absent).
    """

    # Uvicorn logger name for access logs.  Used to detect request boundaries
    # so the contextvar can be cleared when an untraced request starts.
    _ACCESS_LOGGER = "uvicorn.access"

    def filter(self, record: logging.LogRecord) -> bool:
        """Enrich record with OTEL context if available.

        Args:
            record: The log record to enrich.

        Returns:
            Always True (records are never suppressed).
        """
        ids: dict[str, str] = {}
        try:
            from opentelemetry import trace  # type: ignore[import-not-found]

            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                ids = {
                    "traceId": format(ctx.trace_id, "032x"),
                    "spanId": format(ctx.span_id, "016x"),
                }
                # Save for error logs emitted after this span ends.
                _span_context_var.set(ids)
            elif record.name == self._ACCESS_LOGGER:
                # New request boundary with no active span — this request is not
                # traced.  Clear the contextvar so subsequent error logs for this
                # request do not inherit the previous request's trace IDs.
                _span_context_var.set({})
            else:
                # Error/other log — span may have just ended; use the fallback.
                ids = _span_context_var.get()
        except ImportError:
            pass

        for key, value in ids.items():
            record.__dict__[key] = value

        return True


class UvicornJsonFormatter(logging.Formatter):
    """Format log records as single-line JSON following the OTEL Log Data Model.

    Top-level fields (``timestamp``, ``severityText``, ``body``, ``traceId``,
    ``spanId``) follow the OTEL log record schema.  All domain-specific fields
    (logger name, HTTP attributes, exception) are placed inside ``attributes``
    following OTEL semantic conventions.

    Access log records produced by Uvicorn carry request/response values as
    positional args; this formatter extracts them into the ``attributes`` dict
    as ``http.request.method``, ``url.path``, ``url.query`` (when present),
    ``client.address``, and ``http.response.status_code``.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Serialise *record* to a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string.
        """
        payload: dict[str, Any] = {
            "timestamp": _iso_timestamp(record.created),
            "severityText": _SEVERITY_MAP.get(record.levelname, record.levelname),
            "body": record.getMessage(),
        }

        for field in ("traceId", "spanId"):
            value = record.__dict__.get(field)
            if value:
                payload[field] = value

        attributes: dict[str, Any] = {"logger.name": record.name}

        if record.name == "uvicorn.access":
            attributes.update(_extract_http_attributes(record))

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            if exc_type is not None:
                attributes["exception.type"] = exc_type.__qualname__
            if exc_value is not None:
                attributes["exception.message"] = str(exc_value)
            attributes["exception.stacktrace"] = self.formatException(record.exc_info)

        payload["attributes"] = attributes

        return json.dumps(payload, default=str)


def _extract_http_attributes(record: logging.LogRecord) -> dict[str, Any]:
    """Extract HTTP semantic-convention attributes from a Uvicorn access log record.

    Uvicorn emits access logs as::

        access_logger.info('%s - "%s %s HTTP/%s" %d',
                           client_addr, method, path_with_query,
                           http_version, status_code)

    The logger name (``uvicorn.access``) is the stable contract; the positional
    args shape is an implementation detail, so extraction is bounds-checked via
    ``len()`` to be forward-compatible with Uvicorn changes.

    Args:
        record: A log record whose ``name`` is ``uvicorn.access``.

    Returns:
        Dict of OTEL HTTP semantic-convention fields, possibly empty.
    """
    attrs: dict[str, Any] = {}
    args = record.args if isinstance(record.args, (tuple, list)) else ()
    client_addr = str(args[0]) if len(args) > 0 else None
    method = str(args[1]) if len(args) > 1 else None
    path_with_query = str(args[2]) if len(args) > 2 else None
    status_code = args[4] if len(args) > 4 else None

    if method:
        attrs["http.request.method"] = method
    if path_with_query:
        path, _, query = path_with_query.partition("?")
        attrs["url.path"] = path
        if query:
            attrs["url.query"] = query
    if client_addr:
        # Uvicorn produces "host:port" via get_client_addr(); strip the port.
        host, _, _port = client_addr.rpartition(":")
        attrs["client.address"] = host if host else client_addr
    if status_code is not None:
        try:
            attrs["http.response.status_code"] = int(str(status_code))
        except (ValueError, TypeError):
            attrs["http.response.status_code"] = status_code
    return attrs


def _iso_timestamp(epoch: float) -> str:
    """Return an ISO-8601 UTC timestamp string for *epoch* (seconds since epoch)."""
    millis = int((epoch % 1) * 1000)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(epoch)) + f".{millis:03d}Z"
