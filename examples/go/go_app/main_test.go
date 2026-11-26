// Copyright 2026 Canonical Ltd.
// See LICENSE file for licensing details.

package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestNoOIDCRoutesWithoutClient(t *testing.T) {
	t.Setenv("APP_OIDC_REDIRECT_PATH", "")
	mux := http.NewServeMux()
	h := mainHandler{}
	h.registerOIDC(mux)
	response := httptest.NewRecorder()
	mux.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/login/openid-connect", nil))
	if response.Code != http.StatusNotFound {
		t.Fatalf("login without OIDC returned %d, want 404", response.Code)
	}
}

func TestNewConfigUsesFrameworkEndpointEnvironment(t *testing.T) {
	t.Setenv("APP_BASE_URL", "http://example.com")
	t.Setenv("PORT", "9090")
	t.Setenv("METRICS_PORT", "9091")
	t.Setenv("METRICS_PATH", "/custom-metrics")
	t.Setenv("APP_PORT", "7070")
	t.Setenv("APP_METRICS_PORT", "7071")
	t.Setenv("APP_METRICS_PATH", "/old-metrics")

	config, err := NewConfig()
	if err != nil {
		t.Fatalf("NewConfig() returned an error: %v", err)
	}

	if config.Port != "9090" {
		t.Errorf("Port = %q, want %q", config.Port, "9090")
	}
	if config.MetricsPort != "9091" {
		t.Errorf("MetricsPort = %q, want %q", config.MetricsPort, "9091")
	}
	if config.MetricsPath != "/custom-metrics" {
		t.Errorf("MetricsPath = %q, want %q", config.MetricsPath, "/custom-metrics")
	}
}
