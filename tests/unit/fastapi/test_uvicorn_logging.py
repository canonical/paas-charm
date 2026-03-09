# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for Uvicorn JSON logging and OTEL trace/span correlation.

Runs a real Uvicorn process using the template files that the FastAPI charm
pushes into the container (``uvicorn-log-config.json`` and
``uvicorn_log_handler.py``), together with a minimal FastAPI app instrumented
with ``opentelemetry-instrumentation-fastapi``.

Two behaviours are verified:

1. Access logs receive ``trace.id`` / ``span.id`` while the OTEL span is active.
2. Error logs ("Exception in ASGI application") also receive ``trace.id`` —
   injected via the ``ContextVar`` fallback in ``OtelCorrelationFilter`` because
   the OTEL ASGI middleware ends the span before Uvicorn emits the error log.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.request
from typing import Iterator

import pytest

_PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
_TEMPLATES_DIR = _PROJECT_ROOT / "src" / "paas_charm" / "templates" / "fastapi"
_LOG_CONFIG = _TEMPLATES_DIR / "uvicorn-log-config.json"

_APP_HOST = "127.0.0.1"
_APP_PORT = 18082

# Minimal FastAPI app with OTEL instrumentation.
# /ok returns 200; /fail raises ValueError → 500.
_APP_CODE = """
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

trace.set_tracer_provider(TracerProvider())

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

@app.get("/ok")
def ok():
    return {"ok": True}

@app.get("/fail")
def fail():
    raise ValueError("intentional error")
"""


@pytest.fixture(scope="module")
def uvicorn_logs() -> Iterator[dict[str, list[dict]]]:
    """Start Uvicorn, make one /ok and one /fail request, yield parsed log lines."""
    with tempfile.TemporaryDirectory() as d:
        app_file = pathlib.Path(d) / "app.py"
        app_file.write_text(_APP_CODE)

        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{_TEMPLATES_DIR}:{existing_pythonpath}"
            if existing_pythonpath
            else str(_TEMPLATES_DIR)
        )

        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app:app",
                "--host",
                _APP_HOST,
                "--port",
                str(_APP_PORT),
                "--log-config",
                str(_LOG_CONFIG),
            ],
            cwd=d,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            # Poll for readiness instead of a fixed sleep.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(f"http://{_APP_HOST}:{_APP_PORT}/ok", timeout=1):
                        break
                except (urllib.error.URLError, OSError):
                    time.sleep(0.2)
            else:
                raise RuntimeError("Uvicorn did not start within 10 seconds")

            for path in ["/ok", "/fail"]:
                try:
                    with urllib.request.urlopen(
                        f"http://{_APP_HOST}:{_APP_PORT}{path}", timeout=2
                    ):
                        pass
                except urllib.error.HTTPError:
                    pass  # 500 from /fail is expected

            time.sleep(0.5)
        finally:
            proc.terminate()
            out, err = proc.communicate(timeout=5)

    def _parse(stream: bytes) -> list[dict]:
        lines = []
        for line in stream.decode().splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return lines

    yield {
        "stdout": _parse(out),  # uvicorn.access logs
        "stderr": _parse(err),  # uvicorn.error logs (startup, exceptions)
    }


def test_access_log_has_trace_id(  # pylint: disable=redefined-outer-name
    uvicorn_logs: dict,
) -> None:
    """
    arrange: OTEL-instrumented FastAPI app running under Uvicorn with JSON log config.
    act:     make a GET /ok request.
    assert:  the access log line for that request includes trace.id and span.id.
    """
    access_logs = uvicorn_logs["stdout"]
    ok_access = [
        log
        for log in access_logs
        if log.get("log.logger") == "uvicorn.access" and "/ok" in log.get("url.path", "")
    ]
    assert ok_access, "No access log found for /ok"
    record = ok_access[0]

    assert "trace.id" in record, f"trace.id missing from /ok access log: {record}"
    assert "span.id" in record, f"span.id missing from /ok access log: {record}"
    assert len(record["trace.id"]) == 32, "trace.id should be 32-char hex"
    assert len(record["span.id"]) == 16, "span.id should be 16-char hex"


def test_exception_error_log_has_trace_id(  # pylint: disable=redefined-outer-name
    uvicorn_logs: dict,
) -> None:
    """
    arrange: OTEL-instrumented FastAPI app running under Uvicorn with JSON log config.
    act:     make a GET /fail request (raises ValueError → 500).
    assert:  the "Exception in ASGI application" error log has trace.id correlated
             to the same request via the contextvar fallback in OtelCorrelationFilter.

    Why the contextvar is needed:
      The OTEL ASGI middleware ends the span when the exception propagates through it.
      Uvicorn only logs "Exception in ASGI application" after catching the exception
      from the ASGI call — at that point the span context has already been detached.
      OtelCorrelationFilter saves trace.id to a ContextVar when the access log fires
      (span still live) and reads it back as fallback for the error log.
    """
    error_logs = uvicorn_logs["stderr"]
    exception_logs = [
        log for log in error_logs if "Exception in ASGI application" in log.get("message", "")
    ]
    assert exception_logs, "No 'Exception in ASGI application' log found for /fail"
    record = exception_logs[0]

    assert "trace.id" in record, (
        "trace.id should be present in exception log (saved via contextvar). "
        "If this fails, the contextvar in OtelCorrelationFilter is not working."
    )
    # The error log and the access log for the same request must share trace.id.
    fail_access = [
        log
        for log in uvicorn_logs["stdout"]
        if log.get("log.logger") == "uvicorn.access" and "/fail" in log.get("url.path", "")
    ]
    if fail_access:
        assert (
            record["trace.id"] == fail_access[0]["trace.id"]
        ), "Error log and access log should share the same trace.id"
