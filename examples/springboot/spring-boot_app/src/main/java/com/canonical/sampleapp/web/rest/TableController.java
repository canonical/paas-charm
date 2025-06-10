/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

package com.canonical.sampleapp.web.rest;

import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import com.canonical.sampleapp.service.UserService;

@RestController
@RequestMapping("/table")
public class TableController {

    private final Logger log = LoggerFactory.getLogger(TableController.class);

    private final UserService userService;

    public TableController(UserService userService) {
        this.userService = userService;
    }


    @GetMapping("/{name}")
    public ResponseEntity<String> getTable(@PathVariable String name) {
        log.info("REST request to get Table : {}", name);
        try {
            return ResponseEntity.ok().body(userService.countUsers() + " users found");
        } catch (Exception e) {
            log.error("Error retrieving table: {}", name, e);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Error retrieving table", e);
        }
    }

    public <X> ResponseEntity<X> wrapOrNotFound(Optional<X> maybeResponse) {
        return maybeResponse.map(response -> ResponseEntity.ok().body(response))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    }
}
