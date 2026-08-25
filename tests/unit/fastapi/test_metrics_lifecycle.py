# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""FastAPI metrics server lifecycle tests."""

import ast
import asyncio
import importlib.util
import pathlib
import sys
import types
import unittest.mock

PROJECT_ROOT = pathlib.Path(__file__).parents[3]
METRICS_MODULE = PROJECT_ROOT / "examples" / "fastapi" / "fastapi_app" / "metrics.py"
APP_MODULE = PROJECT_ROOT / "examples" / "fastapi" / "fastapi_app" / "app.py"


def test_app_import_registers_metrics_without_starting_server():
    """
    arrange: Parse the application module imported by Alembic.
    act: Inspect its FastAPI construction and function calls.
    assert: Metrics are registered as a lifespan callback, not started during import.
    """
    module = ast.parse(APP_MODULE.read_text())
    calls = [node for node in ast.walk(module) if isinstance(node, ast.Call)]
    fastapi_call = next(
        call for call in calls if isinstance(call.func, ast.Name) and call.func.id == "FastAPI"
    )

    assert not any(
        isinstance(call.func, ast.Name) and call.func.id == "start_http_server" for call in calls
    )
    assert any(
        keyword.arg == "lifespan"
        and isinstance(keyword.value, ast.Name)
        and keyword.value.id == "metrics_lifespan"
        for keyword in fastapi_call.keywords
    )


def test_metrics_server_starts_only_during_application_lifespan(monkeypatch):
    """
    arrange: Provide a fake Prometheus server and a custom metrics port.
    act: Import the lifecycle module and enter its context twice.
    assert: Import has no side effects and each startup is shut down before the next one.
    """
    server = unittest.mock.MagicMock()
    thread = unittest.mock.MagicMock()
    start_http_server = unittest.mock.MagicMock(return_value=(server, thread))
    prometheus_client = types.SimpleNamespace(start_http_server=start_http_server)
    monkeypatch.setitem(sys.modules, "prometheus_client", prometheus_client)
    monkeypatch.setenv("METRICS_PORT", "9876")
    spec = importlib.util.spec_from_file_location("fastapi_app_metrics", METRICS_MODULE)
    assert spec and spec.loader
    metrics = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(metrics)

    start_http_server.assert_not_called()

    async def run_lifespan() -> None:
        async with metrics.metrics_lifespan(None):
            start_http_server.assert_called_with(port=9876, addr="0.0.0.0")

    asyncio.run(run_lifespan())
    asyncio.run(run_lifespan())

    assert start_http_server.call_count == 2
    assert server.shutdown.call_count == 2
    assert thread.join.call_count == 2
    assert server.server_close.call_count == 2
