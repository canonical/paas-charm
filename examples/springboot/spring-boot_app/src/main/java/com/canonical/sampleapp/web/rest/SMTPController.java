/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

package com.canonical.sampleapp.web.rest;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;

@RequestMapping("/send_mail")
@ConditionalOnProperty(name = "spring.mail.host")
@RestController
public class SMTPController {
    @Autowired
    private JavaMailSender mailSender;

    @GetMapping
    public String sendMail() {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom("tester@example.com");
        message.setTo("test@example.com");
        message.setSubject("hello");
        message.setText("Hello world!");

        mailSender.send(message);
        return "Sent";
    }
}
