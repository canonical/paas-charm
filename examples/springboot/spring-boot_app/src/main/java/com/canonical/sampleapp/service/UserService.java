/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */

package com.canonical.sampleapp.service;

import java.security.SecureRandom;
import java.util.Optional;

import org.apache.commons.lang3.RandomStringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.canonical.sampleapp.domain.User;
import com.canonical.sampleapp.repository.UserRepository;
import com.canonical.sampleapp.service.dto.UserDTO;

/**
 * Service class for managing users.
 */
@Service
@Transactional
public class UserService {

    private final Logger log = LoggerFactory.getLogger(UserService.class);

    private final UserRepository userRepository;

    private final PasswordEncoder passwordEncoder;

    private final int DEF_COUNT = 20;

    private final SecureRandom SECURE_RANDOM;

    public UserService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;

        SECURE_RANDOM = new SecureRandom();
        SECURE_RANDOM.nextBytes(new byte[64]);
    }

    public String generateRandomAlphanumericString() {
        return RandomStringUtils.random(DEF_COUNT, 0, 0, true, true, null, SECURE_RANDOM);
    }

    public User createUser(UserDTO userDTO) {
        User user = new User();
        user.setName(userDTO.getName().toLowerCase());
        String encryptedPassword = passwordEncoder.encode(this.generateRandomAlphanumericString());
        user.setPassword(encryptedPassword);

        userRepository.save(user);
        log.debug("Created Information for User: {}", user);
        return user;
    }

    public Long countUsers() {
        return userRepository.count();
    }

    public String getDatabaseType() {
        try {
            String dataEnvVar = System.getenv().get("spring.datasource.url");
            // Remove "jdbc:" prefix if present
            String url = dataEnvVar.startsWith("jdbc:") ? dataEnvVar.substring(5) : dataEnvVar;
            java.net.URI uri = new java.net.URI(url.replaceFirst(":", "://"));
            String scheme = uri.getScheme();
            return scheme != null ? scheme : "unknown";
        } catch (Exception e) {
            log.error("Could not determine database type", e);
        }
        return "unknown";
    }

    @Transactional(readOnly = true)
    public Optional<User> getUserByName(String name) {
        return userRepository.findOneByName(name);
    }
}
