/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.service;

import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.lang.Nullable;
import org.springframework.stereotype.Component;

import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.Queue;

@ConditionalOnProperty(name = "spring.rabbitmq.host")
@Component
public class MessageService {

	private RabbitTemplate template;

	private Queue queue;

	MessageService(Queue queue, RabbitTemplate template) {
		this.queue = queue;
		this.template = template;
	}

	public void send(String message) {
		this.template.convertAndSend(queue.getName(), message);
	}

	@Nullable
	public String receive() {
		Message message = this.template.receive(queue.getName());
		if (message == null) {
			return null;
		}
		return new String(message.getBody());
	}
}
