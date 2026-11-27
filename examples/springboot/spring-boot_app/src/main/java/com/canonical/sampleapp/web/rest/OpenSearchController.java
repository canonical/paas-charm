/*
* Copyright 2026 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import java.io.IOException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import org.opensearch.client.opensearch.OpenSearchClient;
import org.opensearch.client.opensearch._types.OpenSearchException;

@ConditionalOnProperty(name = "opensearch.uris")
@RestController
@RequestMapping("/opensearch")
public class OpenSearchController {
    private final Logger log = LoggerFactory.getLogger(OpenSearchController.class);

    private final OpenSearchClient client;
    private final String index;

    public OpenSearchController(OpenSearchClient client,
            @Value("${sampleapp.opensearch.index}") String index) {
        this.client = client;
        this.index = index;
    }

    @GetMapping("/status")
    public ResponseEntity<String> getStatus() {
        try {
            client.count(request -> request.index(index));
            return ResponseEntity.ok().body("SUCCESS");
        } catch (IOException | OpenSearchException e) {
            log.error("Failed to connect : {}", e.getMessage());
            return new ResponseEntity<>("FAILURE", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}
