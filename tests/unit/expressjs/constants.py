# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

DEFAULT_LAYER = {
    "services": {
        "expressjs": {
            "override": "replace",
            "startup": "enabled",
            "command": "npm start",
            "env": {
                "NODE_ENV": "production",
            },
            "user": "_daemon_",
            "working-dir": "/app",
        },
    }
}


EXPRESSJS_CONTAINER_NAME = "app"
