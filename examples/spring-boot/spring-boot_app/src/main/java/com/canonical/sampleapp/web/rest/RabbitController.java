package com.canonical.sampleapp.web.rest;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.canonical.sampleapp.service.RabbitMQService;

@RequestMapping("/rabbitmq")
@RestController
public class RabbitController {
    @Autowired
    private RabbitMQService rabbitMQService;

    @PostMapping
    public String sendMessage(@RequestBody String message) {
        rabbitMQService.sendMessage(message);
        return "";
    }

    @GetMapping
    public String receiveMessage() {
        String message = rabbitMQService.receiveMessage();
        return message != null ? message : "No messages available";
    }
}
