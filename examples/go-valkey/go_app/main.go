// Copyright 2025 Canonical Ltd.
// See LICENSE file for licensing details.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/valkey-io/valkey-go"
)

var client valkey.Client

func initValkeyClient() (valkey.Client, error) {
	connectString := os.Getenv("VALKEY_DB_CONNECT_STRING")
	username := os.Getenv("VALKEY_USERNAME")
	password := os.Getenv("VALKEY_PASSWORD")

	if connectString == "" {
		return nil, fmt.Errorf("VALKEY_DB_CONNECT_STRING not set")
	}

	// The connect string is in the format "host:port" (no scheme)
	opts := valkey.ClientOption{
		InitAddress:  []string{connectString},
		Username:     username,
		Password:     password,
		DisableCache: true,
	}

	return valkey.NewClient(opts)
}

func serveHelloWorld(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello, World!")
}

func serveValkey(w http.ResponseWriter, r *http.Request) {
	valkeyEnvVars := []string{
		"VALKEY_DB_CONNECT_STRING",
		"VALKEY_DB_HOSTNAME",
		"VALKEY_DB_PORT",
		"VALKEY_DB_SCHEME",
		"VALKEY_DB_NETLOC",
		"VALKEY_DB_PATH",
		"VALKEY_DB_PARAMS",
		"VALKEY_DB_QUERY",
		"VALKEY_DB_FRAGMENT",
		"VALKEY_DB_NAME",
		"VALKEY_USERNAME",
		"VALKEY_PASSWORD",
		"VALKEY_TLS",
		"VALKEY_MODE",
		"VALKEY_VERSION",
	}

	result := make(map[string]string)
	for _, envVar := range valkeyEnvVars {
		result[envVar] = os.Getenv(envVar)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

func serveWrite(w http.ResponseWriter, r *http.Request) {
	// Expected path: /write/<key>/<value>
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/write/"), "/")
	if len(parts) < 2 {
		http.Error(w, `{"error": "usage: /write/<key>/<value>"}`, http.StatusBadRequest)
		return
	}
	key := parts[0]
	value := strings.Join(parts[1:], "/")

	if client == nil {
		http.Error(w, `{"error": "valkey client not initialized"}`, http.StatusServiceUnavailable)
		return
	}

	ctx := context.Background()
	cmd := client.B().Set().Key(key).Value(value).Build()
	err := client.Do(ctx, cmd).Error()
	if err != nil {
		http.Error(w, fmt.Sprintf(`{"error": %q}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok", "key": key, "value": value})
}

func serveRead(w http.ResponseWriter, r *http.Request) {
	// Expected path: /read/<key>
	key := strings.TrimPrefix(r.URL.Path, "/read/")
	if key == "" {
		http.Error(w, `{"error": "usage: /read/<key>"}`, http.StatusBadRequest)
		return
	}

	if client == nil {
		http.Error(w, `{"error": "valkey client not initialized"}`, http.StatusServiceUnavailable)
		return
	}

	ctx := context.Background()
	cmd := client.B().Get().Key(key).Build()
	val, err := client.Do(ctx, cmd).ToString()
	if err != nil {
		if valkey.IsValkeyNil(err) {
			http.Error(w, fmt.Sprintf(`{"error": "key not found", "key": %q}`, key), http.StatusNotFound)
			return
		}
		http.Error(w, fmt.Sprintf(`{"error": %q}`, err.Error()), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"key": key, "value": val})
}

func main() {
	port := os.Getenv("APP_PORT")
	if port == "" {
		port = "8080"
	}

	// Initialize valkey client (non-fatal if not available at startup)
	var err error
	client, err = initValkeyClient()
	if err != nil {
		log.Printf("Warning: valkey client init failed: %v", err)
	} else {
		log.Println("Valkey client initialized successfully")
		defer client.Close()
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", serveHelloWorld)
	mux.HandleFunc("/valkey", serveValkey)
	mux.HandleFunc("/write/", serveWrite)
	mux.HandleFunc("/read/", serveRead)

	server := &http.Server{
		Addr:    ":" + port,
		Handler: mux,
	}

	go func() {
		log.Printf("Starting server on :%s", port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("HTTP server error: %v", err)
		}
	}()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Println("Shutting down...")
}
