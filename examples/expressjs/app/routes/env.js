/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var express = require('express');
var router = express.Router();


/* GET /env - Return all environment variables */
router.get('/', function (req, res) {
    res.status(200).json(process.env); // Return all environment variables as JSON
  });


/* GET /env/:envvar - Check if a env variable exists */
router.get('/:envvar',  function (req, res) {
const envVar = 'APP_' + req.params.envvar.split('-').join('_').toUpperCase();

  console.log("Checking for env variable:", envVar);
  // Check if the environment variable exists
  const value = process.env[envVar];

  if (value) {
    res.status(200).send(value); // Return the value of the environment variable
  } else {
    res.status(404).send(`Environment variable ${envVar} not found`); // Not found
  }
});

module.exports = router;