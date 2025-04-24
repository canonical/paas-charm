/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var express = require("express");
var router = express.Router();
const nodemailer = require("nodemailer");

mail_obj = {
  host: process.env.SMTP_HOST,
  port: process.env.SMTP_PORT,
  secure: false,
};
const transporter = nodemailer.createTransport(mail_obj);

/* GET send_mail page. */
router.get("/", async function (req, res, next) {
  // send mail with defined transport object
  const info = await transporter.sendMail(
    {
      from: "tester@example.com",
      to: "test@example.com",
      subject: "hello",
      text: "Hello world!",
    },
    (err, info) => {
      console.log(info.envelope);
      console.log(info.messageId);
      console.error(err);
    }
  );

  res.send("Sent");
});

module.exports = router;
