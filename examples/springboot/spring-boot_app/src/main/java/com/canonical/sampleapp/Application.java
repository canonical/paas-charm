/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

package com.canonical.sampleapp;

import java.security.Security;

import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {

	public static void main(String[] args) {
		Security.addProvider(new BouncyCastleProvider());
		SpringApplication.run(Application.class, args);
	}
}
