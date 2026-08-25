/*
* Copyright 2026 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import java.io.IOException;
import java.util.Properties;

import com.canonical.sampleapp.config.ValkeyConfiguration;
import com.canonical.sampleapp.web.rest.ValkeyController;

import io.valkey.springframework.data.valkey.connection.ReactiveValkeyConnectionFactory;
import io.valkey.springframework.data.valkey.core.ReactiveValkeyOperations;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.core.io.ClassPathResource;

class ValkeyConditionTest {
    private final ApplicationContextRunner contextRunner = new ApplicationContextRunner()
            .withUserConfiguration(ValkeyConfiguration.class, ValkeyController.class);

    @Test
    void valkeyIntegrationIsDisabledWithoutRelationProperties() {
        contextRunner.run(context -> {
            assertThat(context).doesNotHaveBean(ReactiveValkeyOperations.class);
            assertThat(context).doesNotHaveBean(ValkeyController.class);
        });
    }

    @Test
    void applicationSelectsLettuceClient() throws IOException {
        Properties properties = new Properties();
        try (var inputStream = new ClassPathResource("application.properties").getInputStream()) {
            properties.load(inputStream);
        }

        assertThat(properties).containsEntry("spring.data.valkey.client-type", "lettuce");
    }

    @Test
    void valkeyIntegrationIsEnabledWithRelationProperties() {
        contextRunner
                .withPropertyValues("spring.data.valkey.host=valkey.example")
                .withBean(ReactiveValkeyConnectionFactory.class,
                        () -> mock(ReactiveValkeyConnectionFactory.class))
                .run(context -> {
                    assertThat(context).hasSingleBean(ReactiveValkeyOperations.class);
                    assertThat(context).hasSingleBean(ValkeyController.class);
                });
    }
}
