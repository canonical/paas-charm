/*
* Copyright 2026 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

import com.canonical.sampleapp.config.ValkeyConfiguration;
import com.canonical.sampleapp.web.rest.ValkeyController;

import io.valkey.springframework.data.valkey.connection.ReactiveValkeyConnectionFactory;
import io.valkey.springframework.data.valkey.core.ReactiveValkeyOperations;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

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
