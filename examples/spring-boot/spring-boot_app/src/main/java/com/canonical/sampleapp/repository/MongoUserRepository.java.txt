package com.canonical.sampleapp.repository;

import java.util.Optional;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;

import com.canonical.sampleapp.domain.MongoUser;

public interface MongoUserRepository extends MongoRepository<MongoUser, String> {

    @Query("{name:'?0'}")
    Optional<MongoUser> findUserByName(String name);

    public long count();

}