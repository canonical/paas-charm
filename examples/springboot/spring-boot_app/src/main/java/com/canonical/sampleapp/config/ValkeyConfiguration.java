/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.ReactiveRedisConnectionFactory;
import org.springframework.data.redis.connection.RedisPassword;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.ReactiveRedisOperations;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import com.canonical.sampleapp.domain.ValkeyUser;

@Configuration
public class ValkeyConfiguration {
    @Bean
    ReactiveRedisConnectionFactory valkeyConnectionFactory() {
        String hostname = System.getenv().getOrDefault("VALKEY_DB_HOSTNAME", "localhost");
        int port = Integer.parseInt(System.getenv().getOrDefault("VALKEY_DB_PORT", "6379"));
        RedisStandaloneConfiguration configuration = new RedisStandaloneConfiguration(hostname, port);
        String username = System.getenv("VALKEY_DB_USERNAME");
        String password = System.getenv("VALKEY_DB_PASSWORD");
        if (username != null) {
            configuration.setUsername(username);
        }
        if (password != null) {
            configuration.setPassword(RedisPassword.of(password));
        }
        return new LettuceConnectionFactory(configuration);
    }

    @Bean
    ReactiveRedisOperations<String, ValkeyUser> valkeyOperations(ReactiveRedisConnectionFactory factory) {
        Jackson2JsonRedisSerializer<ValkeyUser> serializer = new Jackson2JsonRedisSerializer<>(ValkeyUser.class);

        RedisSerializationContext.RedisSerializationContextBuilder<String, ValkeyUser> builder = RedisSerializationContext
                .newSerializationContext(new StringRedisSerializer());

        RedisSerializationContext<String, ValkeyUser> context = builder.value(serializer).build();

        return new ReactiveRedisTemplate<>(factory, context);
    }

}
