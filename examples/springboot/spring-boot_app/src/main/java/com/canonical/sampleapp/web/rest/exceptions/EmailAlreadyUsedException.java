/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

package com.canonical.sampleapp.web.rest.exceptions;

import java.net.URI;

@SuppressWarnings("java:S110") // Inheritance tree of classes should not be too deep
public class EmailAlreadyUsedException extends BadRequestAlertException {

    private static final long serialVersionUID = 1L;

    public EmailAlreadyUsedException() {
        super(URI.create("/email-already-used"), "Email is already in use!", "userManagement", "emailexists");
    }
}
