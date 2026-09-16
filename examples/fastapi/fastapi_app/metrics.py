# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Manage the example FastAPI application's Prometheus server lifecycle."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


@asynccontextmanager
async def metrics_lifespan(_: object) -> AsyncIterator[None]:
    """Run the Prometheus HTTP server only while the FastAPI application is running."""
    from prometheus_client import start_http_server

    server, thread = start_http_server(
        port=int(os.getenv("METRICS_PORT", "9464")),
        addr="0.0.0.0",
    )
    try:
        yield
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
