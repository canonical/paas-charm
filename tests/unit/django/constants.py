# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

DEFAULT_LAYER = {
    "services": {
        "django": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/python3 -m gunicorn -c /django/gunicorn.conf.py django_app.wsgi:application -k [ sync ]",
            "after": ["statsd-exporter"],
            "user": "_daemon_",
        },
        "statsd-exporter": {
            "override": "merge",
            "command": (
                "/bin/statsd_exporter --statsd.mapping-config=/statsd-mapping.conf "
                "--statsd.listen-udp=localhost:9125 "
                "--statsd.listen-tcp=localhost:9125"
            ),
            "summary": "statsd exporter service",
            "startup": "enabled",
            "user": "_daemon_",
        },
    }
}

DJANGO_CONTAINER_NAME = "django-app"
