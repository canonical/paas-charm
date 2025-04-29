/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var express = require("express");
var router = express.Router();
const db = require("../database");

/* GET /table/:table - Check if a table exists */
router.get("/:table", async function (req, res) {
  const tableName = req.params.table;

  try {
    // Check if the table exists in the database
    const result = await db.oneOrNone(
      `SELECT table_name FROM information_schema.tables WHERE table_name = $1 AND table_schema = 'public'`,
      [tableName]
    );

    if (result) {
      res.status(200).send("SUCCESS"); // Table exists
    } else {
      res.status(404).end(); // Table does not exist
    }
  } catch (error) {
    console.error("Error checking table existence:", error);
    res.status(500).end(); // Internal server error
  }
});

module.exports = router;
