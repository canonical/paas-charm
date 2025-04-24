/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var express = require("express");
var router = express.Router();
const db = require("../database");

/* GET users listing. */
router.get("/", function (req, res, next) {
  db.query("SELECT * from USERS")
    .then((data) => {
      console.log("DATA:", data.value);
      res.send(data);
    })
    .catch((error) => {
      console.log("ERROR:", error);
      res.status(500).send("Error retrieving data");
    });
});
/* POST to add a new user. */
router.post("/", async function (req, res, next) {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).send("Username and password are required");
  }

  try {
    // Insert the new user into the USERS table
    await db.none("INSERT INTO USERS (NAME, PASSWORD) VALUES ($1, $2)", [
      username,
      password,
    ]);

    res.status(201).send("User added successfully");
  } catch (error) {
    console.error("ERROR:", error);
    res.status(400).send("Error adding user");
  }
});
module.exports = router;
