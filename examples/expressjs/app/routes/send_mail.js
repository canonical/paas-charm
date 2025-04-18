/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

var express = require('express');
var router = express.Router();
const nodemailer = require("nodemailer");

mail_obj =  {
  host: process.env.SMTP_HOST ,// "smtp.ethereal.email",
  port: process.env.SMTP_PORT,
  secure: false, // true for port 465, false for other ports
  // auth: {
  //   user: process.env.SMTP_USER +"@" + process.env.SMTP_DOMAIN, // generated ethereal user
  //   pass: process.env.SMTP_PASSWORD, // generated ethereal password
  // },
} 
console.log(mail_obj);
const transporter = nodemailer.createTransport(mail_obj);


/* GET send_mail page. */
router.get('/', async function(req, res, next) {
  // send mail with defined transport object
  const info = await transporter.sendMail({
    from: '"Maddison Foo Koch 👻" <tester@example.com>', // sender address
    to: "test@example.com",//"bar@example.com, baz@example.com", // list of receivers
    subject: "hello", // Subject line
    text: "Hello world!", // plain text body
  }, (err, info) => {
    console.log(info.envelope);
    console.log(info.messageId);
    console.error(err);
});

  // console.log("Message sent: %s", info.messageId);
  res.send("Sent");
});

module.exports = router;
