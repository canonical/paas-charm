/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.canonical.sampleapp.domain.ValkeyUser;

import io.valkey.springframework.data.valkey.core.ReactiveValkeyOperations;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@ConditionalOnProperty(name = "spring.data.valkey.host")
@RestController
@RequestMapping("/valkey")
public class ValkeyController {
    private final ReactiveValkeyOperations<String, ValkeyUser> valkeyOps;

    ValkeyController(ReactiveValkeyOperations<String, ValkeyUser> valkeyOps) {
        this.valkeyOps = valkeyOps;
    }

    @PostMapping
    public Mono<ResponseEntity<ValkeyUser>> createUser(@RequestBody ValkeyUser user) {
        return valkeyOps.opsForValue().set(user.id(), user)
                .then(Mono.just(new ResponseEntity<>(user, HttpStatus.CREATED)))
                .onErrorReturn(new ResponseEntity<>(HttpStatus.INTERNAL_SERVER_ERROR));
    }

    @GetMapping("/status")
    public Flux<ResponseEntity<String>> getStatus() {
        return valkeyOps.execute(connection -> connection.ping())
                .map(ping -> new ResponseEntity<>("SUCCESS", HttpStatus.OK))
                .onErrorReturn(new ResponseEntity<>("FAILURE", HttpStatus.INTERNAL_SERVER_ERROR));

    }

    @GetMapping("/{id}")
    public Mono<ResponseEntity<ValkeyUser>> getUser(@PathVariable String id) {
        return valkeyOps.opsForValue().get(id)
                .map(user -> new ResponseEntity<>(user, HttpStatus.OK))
                .defaultIfEmpty(new ResponseEntity<>(HttpStatus.NOT_FOUND));
    }
}
