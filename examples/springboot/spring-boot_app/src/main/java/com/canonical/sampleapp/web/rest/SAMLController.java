/*  
 * Copyright 2025 Canonical Ltd.  
 * See LICENSE file for licensing details.  
 */

package com.canonical.sampleapp.web.rest;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.saml2.provider.service.authentication.Saml2AuthenticatedPrincipal;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.RequestMapping;

@ConditionalOnProperty(name = "spring.security.saml2.relyingparty.registration.testentity.entity-id")
@Controller
public class SAMLController {
    // saml endpoint is reserved
    @RequestMapping("/samltest")
    public String saml(@AuthenticationPrincipal Saml2AuthenticatedPrincipal principal, Model model) {
        model.addAttribute("name", principal.getName());
        model.addAttribute("emailAddress", principal.getFirstAttribute("email"));
        model.addAttribute("userAttributes", principal.getAttributes());
        return "saml";
    }
}
