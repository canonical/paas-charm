// Copyright 2025 Canonical Ltd.
// See LICENSE file for licensing details.

package main

import (
	"context"
	"errors"
	"fmt"
	"go-app/internal/service"
	"io"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"encoding/json"
	"net/http"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type mainHandler struct {
	counter prometheus.Counter
	service service.Service
}

func (h mainHandler) serveHelloWorld(w http.ResponseWriter, r *http.Request) {
	h.counter.Inc()
	log.Printf("Counter %#v\n", h.counter)
	fmt.Fprintf(w, "Hello, World!")
}

func (h mainHandler) serveUserDefinedConfig(w http.ResponseWriter, r *http.Request) {
	h.counter.Inc()

	w.Header().Set("Content-Type", "application/json")

	user_defined_config, found := os.LookupEnv("APP_USER_DEFINED_CONFIG")
	if !found {
		json.NewEncoder(w).Encode(nil)
		return
	}
	json.NewEncoder(w).Encode(user_defined_config)
}

func (h mainHandler) servePostgresql(w http.ResponseWriter, r *http.Request) {
	err := h.service.CheckPostgresqlMigrateStatus()
	if err != nil {
		log.Printf(err.Error())
		io.WriteString(w, "FAILURE")
		return
	} else {
		io.WriteString(w, "SUCCESS")
	}
}

func main() {
	metricsPort, found := os.LookupEnv("APP_METRICS_PORT")
	if !found {
		metricsPort = "8080"
	}
	metricsPath, found := os.LookupEnv("APP_METRICS_PATH")
	if !found {
		metricsPath = "/metrics"
	}
	port, found := os.LookupEnv("APP_PORT")
	if !found {
		port = "8080"
	}

	requestCounter := prometheus.NewCounter(
		prometheus.CounterOpts{
			Name: "request_count",
			Help: "No of request handled",
		})
	postgresqlURL := os.Getenv("POSTGRESQL_DB_CONNECT_STRING")

	mux := http.NewServeMux()
	mainHandler := mainHandler{
		counter: requestCounter,
		service: service.Service{PostgresqlURL: postgresqlURL},
	}
	mux.HandleFunc("/", mainHandler.serveHelloWorld)
	mux.HandleFunc("/env/user-defined-config", mainHandler.serveUserDefinedConfig)
	mux.HandleFunc("/postgresql/migratestatus", mainHandler.servePostgresql)

	if metricsPort != port {
		prometheus.MustRegister(requestCounter)

		prometheusMux := http.NewServeMux()
		prometheusMux.Handle(metricsPath, promhttp.Handler())
		prometheusServer := &http.Server{
			Addr:    ":" + metricsPort,
			Handler: prometheusMux,
		}
		go func() {
			if err := prometheusServer.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
				log.Fatalf("Prometheus HTTP server error: %v", err)
			}
			log.Println("Prometheus HTTP Stopped serving new connections.")
		}()
	} else {
		mux.Handle("/metrics", promhttp.Handler())
	}

	server := &http.Server{
		Addr:    ":" + port,
		Handler: mux,
	}
	go func() {
		if err := server.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("HTTP server error: %v", err)
		}
		log.Println("Stopped serving new connections.")
	}()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	shutdownCtx, shutdownRelease := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownRelease()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Fatalf("HTTP shutdown error: %v", err)
	}
	log.Println("Graceful shutdown complete.")
}
