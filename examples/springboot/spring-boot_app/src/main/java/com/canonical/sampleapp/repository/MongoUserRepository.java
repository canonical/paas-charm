/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.repository;

import java.util.Optional;

import org.springframework.data.mongodb.repository.MongoRepository;

import com.canonical.sampleapp.domain.MongoUser;

public interface MongoUserRepository extends MongoRepository<MongoUser, String> {

    Optional<MongoUser> findUserByName(String name);

    public long count();

}
