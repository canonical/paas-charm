# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

DEFAULT_LAYER = {
    "services": {
        "go": {
            "override": "replace",
            "startup": "enabled",
            "command": "/usr/local/bin/go-k8s",
            "user": "_daemon_",
            "working-dir": "/app",
        },
    }
}


GO_CONTAINER_NAME = "app"
