# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

DEFAULT_LAYER = {
    "services": {
        "fastapi": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/python3 -m uvicorn app:app",
            "user": "_daemon_",
            "working-dir": "/app",
        },
    }
}


FASTAPI_CONTAINER_NAME = "app"
