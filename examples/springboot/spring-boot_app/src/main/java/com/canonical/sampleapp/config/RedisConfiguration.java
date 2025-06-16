/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.ReactiveRedisConnectionFactory;
import org.springframework.data.redis.core.ReactiveRedisOperations;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import com.canonical.sampleapp.domain.RedisUser;

@Configuration
public class RedisConfiguration {
    @Bean
    ReactiveRedisOperations<String, RedisUser> redisOperations(ReactiveRedisConnectionFactory factory) {
        Jackson2JsonRedisSerializer<RedisUser> serializer = new Jackson2JsonRedisSerializer<>(RedisUser.class);

        RedisSerializationContext.RedisSerializationContextBuilder<String, RedisUser> builder = RedisSerializationContext
                .newSerializationContext(new StringRedisSerializer());

        RedisSerializationContext<String, RedisUser> context = builder.value(serializer).build();

        return new ReactiveRedisTemplate<>(factory, context);
    }

}
