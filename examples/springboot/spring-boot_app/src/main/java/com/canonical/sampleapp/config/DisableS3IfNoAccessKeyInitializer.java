/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.config;

import java.util.HashMap;
import java.util.Map;

import org.springframework.context.ApplicationContextInitializer;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;

// If the AWS S3 access key is not set, disable S3 support in the application context.
public class DisableS3IfNoAccessKeyInitializer
        implements ApplicationContextInitializer<ConfigurableApplicationContext> {
    @Override
    public void initialize(ConfigurableApplicationContext applicationContext) {
        ConfigurableEnvironment env = applicationContext.getEnvironment();
        String accessKey = env.getProperty("spring.cloud.aws.credentials.accessKey");
        if (accessKey == null || accessKey.isBlank()) {
            Map<String, Object> props = new HashMap<>();
            props.put("spring.cloud.aws.s3.enabled", "false");
            env.getPropertySources().addFirst(new MapPropertySource("disableS3IfNoAccessKey", props));
        }
    }
}
