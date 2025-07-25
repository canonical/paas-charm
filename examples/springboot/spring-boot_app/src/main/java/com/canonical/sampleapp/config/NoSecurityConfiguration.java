/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@ConditionalOnMissingBean(SecurityFilterChain.class)
@ConditionalOnProperty(name = "spring.security.saml2.relyingparty.registration.testentity.entity-id", matchIfMissing = true, havingValue = "false")
@ConditionalOnProperty(name = "spring.security.oauth2.client.registration.oidc.client-id", matchIfMissing = true, havingValue = "false")
public class NoSecurityConfiguration {
	@Bean
	public SecurityFilterChain permitAllSecurityFilterChain(HttpSecurity http) throws Exception {
		http.authorizeHttpRequests(authorize -> authorize.anyRequest().permitAll()).csrf(csrf -> csrf.disable());
		return http.build();
	}
}
