/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var express = require('express');
var router = express.Router();

const db = require('../database');
/* GET home page. */
router.get('/', function(req, res, next) {
  res.send("Hello, World!");
});


/* Dynamic database status endpoint. */
router.get('/:dbType/status', async function(req, res) {
  const dbType = req.params.dbType;

  try {
    // Check database connectivity
    if (dbType === 'postgresql' || dbType === 'mysql') {
      await db.query('SELECT 1'); // A simple query to verify the connection
    } else if (dbType === 'mongodb') {
      // Add MongoDB-specific connection check here
      // Example: await mongodbClient.db().command({ ping: 1 });
    } else if (dbType === 'redis') {
      // Add Redis-specific connection check here
      // Example: await redisClient.ping();
    } else {
      return res.status(400).send('Unsupported database type');
    }

    res.status(200).send('SUCCESS');
  } catch (error) {
    console.error(`Database connection error for ${dbType}:`, error);
    res.status(500).send('FAILURE');
  }
});


module.exports = router;
