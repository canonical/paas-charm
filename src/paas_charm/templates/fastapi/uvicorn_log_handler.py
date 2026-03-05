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
from typing import Any


class OtelCorrelationFilter(logging.Filter):
    """Add OpenTelemetry trace/span IDs to log records when an active span exists.

    If opentelemetry-api is not installed, or no span is active, the record is
    passed through unchanged (trace.id and span.id are simply absent).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Enrich *record* with OTEL context if available.

        Args:
            record: The log record to enrich.

        Returns:
            Always True (records are never suppressed).
        """
        try:
            from opentelemetry import trace  # type: ignore[import-not-found]

            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                record.__dict__["trace.id"] = format(ctx.trace_id, "032x")
                record.__dict__["span.id"] = format(ctx.span_id, "016x")
        except ImportError:
            pass
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
