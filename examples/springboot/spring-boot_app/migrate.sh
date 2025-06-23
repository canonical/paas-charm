#!/bin/sh
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

if [ -n "${POSTGRESQL_DB_NAME}" ]; then
    PGPASSWORD="${POSTGRESQL_DB_PASSWORD}" psql -h "${POSTGRESQL_DB_HOSTNAME}" -U "${POSTGRESQL_DB_USERNAME}" "${POSTGRESQL_DB_NAME}" -c "CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name CHAR(50) NOT NULL UNIQUE,
        password CHAR(60) NOT NULL
    );"
fi

if [ -n "${MYSQL_DB_NAME}" ]; then
    mysql -h "${MYSQL_DB_HOSTNAME}" -u "${MYSQL_DB_USERNAME}" --password="${MYSQL_DB_PASSWORD}" -D "${MYSQL_DB_NAME}" -e "CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name CHAR(50) NOT NULL UNIQUE,
        password CHAR(60) NOT NULL
    );"
fi
