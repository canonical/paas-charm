/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import java.util.HashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.client.OAuth2AuthorizeRequest;
import org.springframework.security.oauth2.client.OAuth2AuthorizedClient;
import org.springframework.security.oauth2.client.OAuth2AuthorizedClientManager;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.oauth2.core.OAuth2AccessToken;
import org.springframework.security.oauth2.core.oidc.OidcIdToken;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@ConditionalOnProperty(name = "spring.security.oauth2.client.registration.oidc.client-id")
@RestController
public class OpenIDController {
	private final Logger log = LoggerFactory.getLogger(OpenIDController.class);
	@Autowired
	private OAuth2AuthorizedClientManager oAuth2AuthorizedClientManager;

	@GetMapping("/profile")
	public Map<String, Object> oidc() {
		HashMap<String, Object> response = new HashMap<>();

		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
		if (authentication instanceof OAuth2AuthenticationToken token
				&& token.getPrincipal() instanceof DefaultOidcUser user) {
			OidcIdToken idToken = user.getIdToken();
			log.info("Token raw value: {}", idToken.getTokenValue());
			log.info("Token claims map: {}", idToken.getClaims());

			OAuth2AuthorizeRequest authRequest = OAuth2AuthorizeRequest
					.withClientRegistrationId(token.getAuthorizedClientRegistrationId()).principal(token).build();
			OAuth2AuthorizedClient client = oAuth2AuthorizedClientManager.authorize(authRequest);
			OAuth2AccessToken accessToken = client.getAccessToken();
			log.info("Token raw value: {}", accessToken.getTokenValue());
			log.info("Token scopes: {}", accessToken.getScopes());
			response.put("message", "Welcome, " + idToken.getClaims().get("email") + "!");
			response.put("claims", idToken.getClaims());
		}

		return response;
	}

}
