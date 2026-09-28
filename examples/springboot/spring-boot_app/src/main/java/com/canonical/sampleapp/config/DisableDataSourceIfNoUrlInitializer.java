/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.config;

import java.util.HashMap;
import java.util.Map;

import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;
import org.springframework.context.ApplicationContextInitializer;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;

// If no database URL is provided, disable the datasource (and the JPA
// autoconfiguration that depends on it) so the application can start without a
// database integration.
public class DisableDataSourceIfNoUrlInitializer
        implements ApplicationContextInitializer<ConfigurableApplicationContext> {
    @Override
    public void initialize(ConfigurableApplicationContext applicationContext) {
        ConfigurableEnvironment env = applicationContext.getEnvironment();
        String url = env.getProperty("spring.datasource.url");
        if (url == null || url.isBlank()) {
            Map<String, Object> props = new HashMap<>();
            props.put("spring.autoconfigure.exclude", DataSourceAutoConfiguration.class.getName());
            env.getPropertySources().addFirst(new MapPropertySource("disableDataSourceIfNoUrl", props));
        }
    }
}
