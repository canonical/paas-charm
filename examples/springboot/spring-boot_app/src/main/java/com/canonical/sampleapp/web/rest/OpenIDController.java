/*
* Copyright 2025 Canonical Ltd.
* See LICENSE file for licensing details.
*/

package com.canonical.sampleapp.web.rest;

import java.util.HashMap;
import java.util.Map;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.oauth2.core.oidc.OidcIdToken;
import org.springframework.security.oauth2.core.oidc.user.DefaultOidcUser;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@ConditionalOnProperty(name = "spring.security.oauth2.client.registration.oidc.client-id")
@RestController
public class OpenIDController {

	@GetMapping("/profile")
	public Map<String, Object> oidc() {
		HashMap<String, Object> response = new HashMap<>();

		Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
		if (authentication instanceof OAuth2AuthenticationToken token
				&& token.getPrincipal() instanceof DefaultOidcUser user) {
			OidcIdToken idToken = user.getIdToken();
			response.put("message", "Welcome, " + idToken.getClaims().get("email") + "!");
			response.put("claims", idToken.getClaims());
		}

		return response;
	}

}
