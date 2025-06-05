/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

package com.canonical.sampleapp.web.rest;

import java.lang.management.ManagementFactory;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class EnvController {
    @Value("${greeting:Hello}")
    private String greeting;

    @GetMapping(value = "/hello-world", produces = MediaType.APPLICATION_JSON_VALUE)
    public Map<String, String> helloWorld() {
        return Collections.singletonMap("response", String.format("%s, World!", greeting));
    }

    @GetMapping(value = "/jvm-arguments", produces = MediaType.APPLICATION_JSON_VALUE)
    public List<String> jvmArguments() {
        return ManagementFactory.getRuntimeMXBean().getInputArguments();
    }
}
