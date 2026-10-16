var express = require('express');
var router = express.Router();

router.get('/', function(req, res, next) {
  res.type("text/plain").send("Hello world!");
});

module.exports = router;
