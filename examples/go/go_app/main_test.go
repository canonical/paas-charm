// Copyright 2026 Canonical Ltd.
// See LICENSE file for licensing details.

package main

import "testing"

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
