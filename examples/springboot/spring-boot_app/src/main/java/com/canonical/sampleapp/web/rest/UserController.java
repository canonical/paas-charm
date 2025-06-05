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
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import com.canonical.sampleapp.domain.User;
import com.canonical.sampleapp.service.UserService;
import com.canonical.sampleapp.service.dto.UserDTO;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/users")
public class UserController {

    private final Logger log = LoggerFactory.getLogger(UserController.class);

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping
    public ResponseEntity<User> createUser(@Valid @RequestBody UserDTO userDTO) throws URISyntaxException {
        log.debug("REST request to create User : {}", userDTO);
        if (userService.getUserByName(userDTO.getName()).isPresent()) {
            User existingUser = userService.getUserByName(userDTO.getName()).get();
            return ResponseEntity.badRequest().body(existingUser);
        }
        User newUser = userService.createUser(userDTO);
        return ResponseEntity
                .created(new URI("/users/" + newUser.getName()))
                .body(newUser);
    }

    @GetMapping("/{name}")
    public ResponseEntity<UserDTO> getUser(@PathVariable String name) {
        log.debug("REST request to get User : {}", userService.getUserByName(name).map(UserDTO::new));
        return this.wrapOrNotFound(userService.getUserByName(name).map(UserDTO::new));
    }

    public <X> ResponseEntity<X> wrapOrNotFound(Optional<X> maybeResponse) {
        return maybeResponse.map(response -> ResponseEntity.ok().body(response))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    }
}
