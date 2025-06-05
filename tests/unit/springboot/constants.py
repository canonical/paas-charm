# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

DEFAULT_LAYER = {
    "services": {
        "spring-boot": {
            "override": "replace",
            "startup": "enabled",
            "command": '/bash -c "java -jar *.jar"',
            "user": "_daemon_",
            "working-dir": "/app",
        },
    }
}


SPRINGBOOT_CONTAINER_NAME = "app"
