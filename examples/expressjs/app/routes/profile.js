/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var express = require('express');
var router = express.Router();


/* GET user profile. */
router.get('/', function(req, res, next) {
  res.render('profile', { user: req.oidc.user });
});

module.exports = router;
