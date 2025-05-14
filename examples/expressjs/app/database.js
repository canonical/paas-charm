/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

const pgp = require("pg-promise")(/* options */);
const PG_CONNECT_STR = process.env["POSTGRESQL_DB_CONNECT_STRING"];

console.log("PG_CONNECT_STR", PG_CONNECT_STR);
let db = null;

if (PG_CONNECT_STR) {
  db = pgp(PG_CONNECT_STR);
}

module.exports = db;
