/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import java.util.stream.Collectors;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import dev.openfga.sdk.api.client.OpenFgaClient;
import dev.openfga.sdk.api.model.AuthorizationModel;

@RestController
@ConditionalOnProperty(name = "openfga.api-url")
@RequestMapping("/openfga")
public class OpenFgaController {

    private final OpenFgaClient openFgaClient;

    public OpenFgaController(OpenFgaClient openFgaClient) {
        this.openFgaClient = openFgaClient;
    }

    @GetMapping("/list-authorization-models")
    public ResponseEntity<String> listAuthorizationModels() {
        try {
            var response = openFgaClient.readAuthorizationModels().join();
            var modelIds = response.getAuthorizationModels().stream()
                    .map(AuthorizationModel::getId)
                    .collect(Collectors.joining(", "));
            return ResponseEntity.ok("Listed authorization models: " + modelIds);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body("Failed to list authorization models: " + e.getMessage());
        }
    }
}
