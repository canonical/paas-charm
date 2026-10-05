#!/usr/bin/bash
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

if [ -n "${POSTGRESQL_DB_NAME}" ]; then
    python3 manage.py migrate
fi
