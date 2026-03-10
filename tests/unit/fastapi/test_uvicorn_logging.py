# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for Uvicorn JSON logging and OTEL trace/span correlation.

All tests operate directly on ``OtelCorrelationFilter`` and
``UvicornJsonFormatter`` — no subprocess or network I/O required.
End-to-end verification (real Uvicorn + charm) is covered by the integration
tests in ``tests/integration/fastapi/test_fastapi.py``.
"""

import json
import logging
import sys
import unittest.mock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import (  # pylint: disable=import-error,no-name-in-module
    TracerProvider,
)
from uvicorn_log_handler import (  # pylint: disable=import-error
    OtelCorrelationFilter,
    UvicornJsonFormatter,
    _span_context_var,
)

trace.set_tracer_provider(TracerProvider())
_TRACER = trace.get_tracer("test")


@pytest.fixture(autouse=True)
def _reset_span_contextvar():
    """Clear the span contextvar before each test to prevent state leakage."""
    _span_context_var.set({})
    yield
    _span_context_var.set({})


def test_filter_injects_trace_ids_when_span_active() -> None:
    """
    arrange: an active OTEL span.
    act: run OtelCorrelationFilter on a log record.
    assert: traceId and spanId are injected into the record.
    """
    flt = OtelCorrelationFilter()
    record = _make_record()
    with _TRACER.start_as_current_span("req"):
        flt.filter(record)
    assert "traceId" in record.__dict__, "traceId should be injected"
    assert "spanId" in record.__dict__, "spanId should be injected"
    assert len(record.__dict__["traceId"]) == 32
    assert len(record.__dict__["spanId"]) == 16


def test_filter_contextvar_fallback_for_error_log() -> None:
    """
    arrange: an access log record filtered while a span is active, then the span ends.
    act: run the filter on a subsequent error log record (no active span).
    assert: the error record carries the traceId saved to the contextvar by the access log.
    """
    flt = OtelCorrelationFilter()
    access_record = _make_record(name="uvicorn.access", level=logging.INFO)
    error_record = _make_record(name="uvicorn.error")

    with _TRACER.start_as_current_span("req"):
        flt.filter(access_record)

    saved_trace_id = access_record.__dict__.get("traceId")
    assert saved_trace_id, "traceId should have been injected into access record"

    flt.filter(error_record)
    assert (
        error_record.__dict__.get("traceId") == saved_trace_id
    ), "Error log should carry traceId from contextvar fallback"


def test_filter_clears_contextvar_on_untraced_access_log() -> None:
    """
    arrange: a traced request followed by an untraced request on the same connection.
    act: filter the traced access log (span active), then the untraced access log (no span).
    assert: the contextvar is cleared and the subsequent error log carries no stale traceId.
    """
    flt = OtelCorrelationFilter()

    traced_access = _make_record(name="uvicorn.access", level=logging.INFO)
    with _TRACER.start_as_current_span("req"):
        flt.filter(traced_access)
    assert _span_context_var.get(), "contextvar should be populated after traced request"

    untraced_access = _make_record(name="uvicorn.access", level=logging.INFO)
    flt.filter(untraced_access)

    assert not _span_context_var.get(), "contextvar should be cleared at untraced request boundary"

    error_record = _make_record(name="uvicorn.error")
    flt.filter(error_record)
    assert (
        "traceId" not in error_record.__dict__
    ), "traceId from previous traced request must not leak into untraced error log"


def test_filter_passthrough_without_otel() -> None:
    """
    arrange: opentelemetry is not installed (modules patched out of sys.modules).
    act: run OtelCorrelationFilter on a log record.
    assert: the record passes through unchanged with no traceId or spanId.
    """
    flt = OtelCorrelationFilter()
    record = _make_record()
    with unittest.mock.patch.dict(
        sys.modules, {"opentelemetry": None, "opentelemetry.trace": None}
    ):
        flt.filter(record)
    assert "traceId" not in record.__dict__, "traceId should be absent without OTEL"
    assert "spanId" not in record.__dict__, "spanId should be absent without OTEL"


def test_exception_fields_present() -> None:
    """
    arrange: a log record with exc_info set from a live ValueError.
    act: format the record with UvicornJsonFormatter.
    assert: exception.type, exception.message, and exception.stacktrace are in attributes.
    """
    record = _make_record(exc_info=True)
    payload = json.loads(UvicornJsonFormatter().format(record))
    attrs = payload["attributes"]
    assert attrs["exception.type"] == "ValueError"
    assert attrs["exception.message"] == "bad input"
    assert "exception.stacktrace" in attrs


def test_no_exception_fields_without_exc_info() -> None:
    """
    arrange: a log record with no exception attached.
    act: format the record with UvicornJsonFormatter.
    assert: exception fields are absent from attributes.
    """
    record = _make_record(exc_info=False)
    payload = json.loads(UvicornJsonFormatter().format(record))
    attrs = payload["attributes"]
    assert "exception.type" not in attrs
    assert "exception.message" not in attrs
    assert "exception.stacktrace" not in attrs


def _make_record(
    name: str = "uvicorn.error",
    level: int = logging.ERROR,
    msg: str = "test",
    exc_info: bool = False,
) -> logging.LogRecord:
    """Return a LogRecord, optionally with exc_info from a live exception."""
    logger = logging.getLogger(name)
    record = logger.makeRecord(name, level, "<test>", 0, msg, (), None)
    if exc_info:
        try:
            raise ValueError("bad input")
        except ValueError:
            record.exc_info = sys.exc_info()
    return record
