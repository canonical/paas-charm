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


# ---------------------------------------------------------------------------
# OtelCorrelationFilter tests
# ---------------------------------------------------------------------------


def test_filter_injects_trace_ids_when_span_active() -> None:
    """Active span → traceId and spanId are injected into the record."""
    flt = OtelCorrelationFilter()
    record = _make_record()
    with _TRACER.start_as_current_span("req"):
        flt.filter(record)
    assert "traceId" in record.__dict__, "traceId should be injected"
    assert "spanId" in record.__dict__, "spanId should be injected"
    assert len(record.__dict__["traceId"]) == 32
    assert len(record.__dict__["spanId"]) == 16


def test_filter_contextvar_fallback_for_error_log() -> None:
    """Error log after span ends still receives traceId via contextvar fallback."""
    flt = OtelCorrelationFilter()
    access_record = _make_record(name="uvicorn.access", level=logging.INFO)
    error_record = _make_record(name="uvicorn.error")

    # Simulate: access log fires while span is active (saves to contextvar).
    with _TRACER.start_as_current_span("req"):
        flt.filter(access_record)

    saved_trace_id = access_record.__dict__.get("traceId")
    assert saved_trace_id, "traceId should have been injected into access record"

    # Simulate: error log fires after span has ended (no active span).
    flt.filter(error_record)
    assert (
        error_record.__dict__.get("traceId") == saved_trace_id
    ), "Error log should carry traceId from contextvar fallback"


def test_filter_clears_contextvar_on_untraced_access_log() -> None:
    """Untraced access log clears contextvar — prevents keep-alive ID leakage."""
    flt = OtelCorrelationFilter()

    # First request: traced — saves traceId to contextvar.
    traced_access = _make_record(name="uvicorn.access", level=logging.INFO)
    with _TRACER.start_as_current_span("req"):
        flt.filter(traced_access)
    assert _span_context_var.get(), "contextvar should be populated after traced request"

    # Second request: untraced access log — should clear contextvar.
    untraced_access = _make_record(name="uvicorn.access", level=logging.INFO)
    flt.filter(untraced_access)  # no active span

    assert not _span_context_var.get(), "contextvar should be cleared at untraced request boundary"

    # Subsequent error log for the untraced request must not carry stale traceId.
    error_record = _make_record(name="uvicorn.error")
    flt.filter(error_record)
    assert (
        "traceId" not in error_record.__dict__
    ), "traceId from previous traced request must not leak into untraced error log"


def test_filter_passthrough_without_otel() -> None:
    """When opentelemetry is not installed, records pass through unchanged."""
    flt = OtelCorrelationFilter()
    record = _make_record()
    with unittest.mock.patch("builtins.__import__", side_effect=ImportError("no otel")):
        # The filter imports opentelemetry lazily; patch at the import site.
        pass
    # Simulate ImportError by patching the module lookup used inside filter.
    with unittest.mock.patch.dict(
        sys.modules, {"opentelemetry": None, "opentelemetry.trace": None}
    ):
        flt.filter(record)
    assert "traceId" not in record.__dict__, "traceId should be absent without OTEL"
    assert "spanId" not in record.__dict__, "spanId should be absent without OTEL"


# ---------------------------------------------------------------------------
# UvicornJsonFormatter tests
# ---------------------------------------------------------------------------


def test_exception_fields_present() -> None:
    """exception.type and exception.message are set from record.exc_info."""
    record = _make_record(exc_info=True)
    payload = json.loads(UvicornJsonFormatter().format(record))
    attrs = payload["attributes"]
    assert attrs["exception.type"] == "ValueError"
    assert attrs["exception.message"] == "bad input"
    assert "exception.stacktrace" in attrs


def test_no_exception_fields_without_exc_info() -> None:
    """exception fields are absent when no exception is attached."""
    record = _make_record(exc_info=False)
    payload = json.loads(UvicornJsonFormatter().format(record))
    attrs = payload["attributes"]
    assert "exception.type" not in attrs
    assert "exception.message" not in attrs
    assert "exception.stacktrace" not in attrs
