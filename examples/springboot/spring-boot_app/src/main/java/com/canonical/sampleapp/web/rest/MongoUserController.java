/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.canonical.sampleapp.domain.MongoUser;
import com.canonical.sampleapp.repository.MongoUserRepository;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/mongodb")
public class MongoUserController {
    @Autowired
    MongoUserRepository userRepo;
    private final Logger log = LoggerFactory.getLogger(MongoUserController.class);

    @PostMapping("/users")
    public ResponseEntity<MongoUser> createUser(@Valid @RequestBody MongoUser user) throws URISyntaxException {
        // Skip validation as a sample application
        MongoUser result = userRepo.save(user);
        return ResponseEntity.created(new URI("/mongo/users/" + result.getId()))
                .body(result);
    }

    @GetMapping
    public ResponseEntity<MongoUser> getUser(
            @RequestParam(required = true) String name) {
        Optional<MongoUser> user = userRepo.findUserByName(name);
        if (user.isEmpty()) {
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        }
        return new ResponseEntity<>(user.get(), HttpStatus.OK);
    }

    @GetMapping("/status")
    public ResponseEntity<String> getStatus() {
        try {
            userRepo.count();
            return new ResponseEntity<>("SUCCESS", HttpStatus.OK);
        } catch (DataAccessException e) {
            log.error("Failed to connect : {}", e.getMessage());
            return new ResponseEntity<>("FAILURE", HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }
}
