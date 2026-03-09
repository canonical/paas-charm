# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""JSON log formatter and OTEL correlation filter for Uvicorn.

This file is pushed by the charm into /opt/paas_charm/ inside the application
container and loaded by Uvicorn via the UVICORN_LOG_CONFIG environment variable.
It must only depend on the Python standard library; opentelemetry-api is used
only when already installed by the user.
"""

import json
import logging
import time
from contextvars import ContextVar
from typing import Any

# Stores the last known {trace.id, span.id} for the current async context.
# Populated by OtelCorrelationFilter whenever a valid span is active (access log path).
# Read as fallback when the span has already ended (error log path).
#
# Keep-alive note: on HTTP/1.1 connections, multiple requests share the same asyncio
# task and therefore the same ContextVar.  OtelCorrelationFilter detects request
# boundaries via the "uvicorn.access" logger name: if an access log arrives with no
# active span the contextvar is cleared, preventing stale IDs from leaking into
# subsequent untraced requests.
_span_context_var: ContextVar[dict[str, str]] = ContextVar("_span_context_var", default={})


class OtelCorrelationFilter(logging.Filter):
    """Add OpenTelemetry trace/span IDs to log records.

    When a valid OTEL span is active, injects ``trace.id`` and ``span.id``
    into the record **and** saves them to a ``ContextVar`` for later use.

    When no span is active (e.g. error logs emitted after the span has ended),
    falls back to the value saved in the ``ContextVar`` so that error logs
    emitted in the same async task are still correlated to the request.

    If opentelemetry-api is not installed at all, records are passed through
    unchanged (``trace.id`` and ``span.id`` are simply absent).
    """

    # Uvicorn logger name for access logs.  Used to detect request boundaries
    # so the contextvar can be cleared when an untraced request starts.
    _ACCESS_LOGGER = "uvicorn.access"

    def filter(self, record: logging.LogRecord) -> bool:
        """Enrich *record* with OTEL context if available.

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
                    "trace.id": format(ctx.trace_id, "032x"),
                    "span.id": format(ctx.span_id, "016x"),
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
    """Format log records as single-line JSON with ECS-aligned field names.

    Access log records produced by uvicorn carry the raw request/response
    values as a 5-tuple in ``record.args``; this formatter extracts them
    into dedicated HTTP fields.  All other records are formatted with only
    the common fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Serialise *record* to a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string.
        """
        payload: dict[str, Any] = {
            "@timestamp": _iso_timestamp(record.created),
            "log.level": record.levelname.lower(),
            "log.logger": record.name,
            "message": record.getMessage(),
        }

        for field in ("trace.id", "span.id"):
            value = record.__dict__.get(field)
            if value:
                payload[field] = value

        # Uvicorn access records pass args as (client, method, path, version, status)
        if isinstance(record.args, tuple) and len(record.args) == 5:
            _client, method, path, _version, status_code = record.args
            payload["http.request.method"] = method
            payload["url.path"] = path
            payload["http.response.status_code"] = status_code

        if record.exc_info:
            payload["error.stack_trace"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def _iso_timestamp(epoch: float) -> str:
    """Return an ISO-8601 UTC timestamp string for *epoch* (seconds since epoch)."""
    millis = int((epoch % 1) * 1000)
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(epoch)) + f".{millis:03d}Z"
