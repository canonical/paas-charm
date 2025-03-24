# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from secrets import token_hex

DEFAULT_LAYER = {
    "services": {
        "flask": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app -k [ sync ]",
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

LAYER_WITH_WORKER = {
    "services": {
        "flask": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app -k [ sync ]",
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
        "not-worker-service": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/noworker",
            "user": "_daemon_",
        },
        "real-worker": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/worker",
            "user": "_daemon_",
        },
        "Another-Real-WorkeR": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/worker",
            "user": "_daemon_",
        },
        "real-scheduler": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/scheduler",
            "user": "_daemon_",
        },
        "ANOTHER-REAL-SCHEDULER": {
            "override": "replace",
            "startup": "enabled",
            "command": "/bin/worker",
            "user": "_daemon_",
        },
    }
}

FLASK_CONTAINER_NAME = "flask-app"

SAML_APP_RELATION_DATA_EXAMPLE = {
    "entity_id": "https://login.staging.ubuntu.com",
    "metadata_url": "https://login.staging.ubuntu.com/saml/metadata",
    "single_logout_service_redirect_binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
    "single_logout_service_redirect_url": "https://login.staging.ubuntu.com/+logout",
    "single_sign_on_service_redirect_binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
    "single_sign_on_service_redirect_url": "https://login.staging.ubuntu.com/saml/",
    "x509certs": "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",
}

SMTP_RELATION_DATA_EXAMPLE = {
    "auth_type": "none",
    "domain": "example.com",
    "host": "test-ip",
    "port": "1025",
    "skip_ssl_verify": "False",
    "transport_security": "none",
}

INTEGRATIONS_RELATION_DATA = {
    "postgresql": {
        "app_data": {
            "database": "test-database",
            "endpoints": "test-postgresql:5432,test-postgresql-2:5432",
            "password": "test-password",
            "username": "test-username",
        }
    },
    "mongodb": {"app_data": {"uris": "mongodb://foobar/"}},
    "mysql": {
        "app_data": {
            "endpoints": "test-mysql:3306",
            "password": "test-password",
            "username": "test-username",
        }
    },
    "s3": {
        "app_data": {
            "access-key": token_hex(16),
            "secret-key": token_hex(16),
            "bucket": "flask-bucket",
        }
    },
    "redis": {
        "unit_data": {
            "hostname": "10.1.88.132",
            "port": "6379",
        }
    },
    "saml": {"app_data": SAML_APP_RELATION_DATA_EXAMPLE},
}
