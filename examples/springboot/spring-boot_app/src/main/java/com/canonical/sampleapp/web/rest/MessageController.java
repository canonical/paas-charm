/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import com.canonical.sampleapp.service.MessageService;

@ConditionalOnProperty(name = "spring.rabbitmq.host")
@RestController
public class MessageController {

	private final MessageService messageService;

	public MessageController(MessageService messageService) {
		this.messageService = messageService;
	}

	@PostMapping(value = "/rabbitmq/send")
	public ResponseEntity<String> send() {
		messageService.send("SUCCESS");
		return ResponseEntity.ok("SUCCESS");
	}

	@GetMapping(value = "/rabbitmq/receive")
	public ResponseEntity<String> receive() {
		String message = messageService.receive();
		if (message == null) {
			return ResponseEntity.notFound().build();
		}
		return ResponseEntity.ok(message);
	}

}
