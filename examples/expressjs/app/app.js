/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var createError = require("http-errors");
var express = require("express");
var path = require("path");
var cookieParser = require("cookie-parser");
var logger = require("morgan");
const promBundle = require("express-prom-bundle");
// Add the options to the prometheus middleware most option are for http_request_duration_seconds histogram metric
const metricsMiddleware = promBundle({
  includeMethod: true,
});

var indexRouter = require("./routes/index");
var tableRouter = require("./routes/table");
var usersRouter = require("./routes/users");
var mailRouter = require("./routes/send_mail");
var envRouter = require("./routes/env");

require("./instrumentation");

var app = express();

// view engine setup
app.set("views", path.join(__dirname, "views"));
app.set("view engine", "jade");

// add the prometheus middleware to all routes
app.use(metricsMiddleware);

app.use(logger("dev"));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, "public")));

app.use("/users", usersRouter);
app.use("/table", tableRouter);
app.use("/send_mail", mailRouter);
app.use("/env", envRouter);
app.use("/", indexRouter);

// catch 404 and forward to error handler
app.use(function (req, res, next) {
  next(createError(404));
});

// error handler
app.use(function (err, req, res, next) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get("env") === "development" ? err : {};

  // render the error page
  res.status(err.status || 500);
  res.render("error");
});

module.exports = app;
