/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.config;

import com.canonical.sampleapp.domain.ValkeyUser;

import io.valkey.springframework.data.valkey.connection.ReactiveValkeyConnectionFactory;
import io.valkey.springframework.data.valkey.core.ReactiveValkeyOperations;
import io.valkey.springframework.data.valkey.core.ReactiveValkeyTemplate;
import io.valkey.springframework.data.valkey.serializer.Jackson2JsonValkeySerializer;
import io.valkey.springframework.data.valkey.serializer.StringValkeySerializer;
import io.valkey.springframework.data.valkey.serializer.ValkeySerializationContext;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@ConditionalOnProperty(name = "spring.data.valkey.host")
@Configuration
public class ValkeyConfiguration {
    @Bean
    ReactiveValkeyOperations<String, ValkeyUser> valkeyOperations(ReactiveValkeyConnectionFactory factory) {
        Jackson2JsonValkeySerializer<ValkeyUser> serializer = new Jackson2JsonValkeySerializer<>(
                ValkeyUser.class);

        ValkeySerializationContext.ValkeySerializationContextBuilder<String, ValkeyUser> builder = ValkeySerializationContext
                .newSerializationContext(new StringValkeySerializer());

        ValkeySerializationContext<String, ValkeyUser> context = builder.value(serializer).build();

        return new ReactiveValkeyTemplate<>(factory, context);
    }

}
