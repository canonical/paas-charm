#!/bin/sh
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

PGPASSWORD="${POSTGRESQL_DB_PASSWORD}" psql -h "${POSTGRESQL_DB_HOSTNAME}" -U "${POSTGRESQL_DB_USERNAME}" "${POSTGRESQL_DB_NAME}" -c "CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name CHAR(50) NOT NULL UNIQUE,
    password CHAR(60) NOT NULL
);"
