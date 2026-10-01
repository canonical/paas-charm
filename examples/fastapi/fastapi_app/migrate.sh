#! /usr/bin/env bash
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

if [ -n "${POSTGRESQL_DB_CONNECT_STRING}" ]; then
    alembic upgrade head
fi
