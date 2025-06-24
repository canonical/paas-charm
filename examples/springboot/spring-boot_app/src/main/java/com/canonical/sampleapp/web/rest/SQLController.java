/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.dao.DataAccessException;
import com.canonical.sampleapp.service.UserService;

@RestController
public class SQLController {
    private final Logger log = LoggerFactory.getLogger(UserService.class);

    private final UserService userService;

    public SQLController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping(value = "/{dbApp}/status")
    public ResponseEntity<String> mysqlStatus(@PathVariable String dbApp) {
        try {
            if (dbApp.equals(userService.getDatabaseType())) {
                userService.countUsers();
                return ResponseEntity.ok().body("SUCCESS");
            }
        } catch (DataAccessException e) {
            log.error("Database access error connecting to the database " + dbApp, e);
        }
        return ResponseEntity.ok().body("FAILURE");
    }
}
