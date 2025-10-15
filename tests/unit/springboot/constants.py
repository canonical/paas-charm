# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

DEFAULT_LAYER = {
    "services": {
        "spring-boot": {
            "startup": "enabled",
            "override": "replace",
            "command": 'bash -c "java -jar *.jar"',
        },
    }
}

SPRINGBOOT_CONTAINER_NAME = "app"
