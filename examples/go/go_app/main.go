// Copyright 2025 Canonical Ltd.
// See LICENSE file for licensing details.

package main

import (
	"context"
	"crypto/tls"
	"errors"
	"fmt"
	"go-app/internal/service"
	"io"
	"log"
	"net/mail"
	"net/smtp"
	"os"
	"os/signal"
	"syscall"
	"time"

	"encoding/json"
	"net/http"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"

	. "github.com/openfga/go-sdk/client"
	"github.com/openfga/go-sdk/credentials"
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

func handleError(w http.ResponseWriter, error_message error) {
	w.WriteHeader(http.StatusInternalServerError)
	w.Header().Set("Content-Type", "application/json")
	resp := make(map[string]string)
	resp["message"] = error_message.Error()
	jsonResp, err := json.Marshal(resp)
	if err != nil {
		log.Fatalf("Error happened in JSON marshal. Err: %s", err)
	}
	w.Write(jsonResp)
	return
}

func (h mainHandler) serveOpenFgaListAuthorizationModels(w http.ResponseWriter, r *http.Request) {
	h.counter.Inc()
	log.Printf("Counter %#v\n", h.counter)

	fgaClient, err := NewSdkClient(&ClientConfiguration{
		ApiUrl:  os.Getenv("FGA_HTTP_API_URL"),
		StoreId: os.Getenv("FGA_STORE_ID"),
		Credentials: &credentials.Credentials{
			Method: credentials.CredentialsMethodApiToken,
			Config: &credentials.Config{
				ApiToken: os.Getenv("FGA_TOKEN"),
			},
		},
	})
	if err != nil {
		handleError(w, err)
	}

	_, err = fgaClient.ReadAuthorizationModels(context.Background()).Execute()
	if err != nil {
		handleError(w, err)
	}

	fmt.Fprintf(w, "Listed authorization models")
}

func (h mainHandler) serveMail(w http.ResponseWriter, r *http.Request) {
	h.counter.Inc()
	log.Printf("Counter %#v\n", h.counter)

	from := mail.Address{"", "tester@example.com"}
	to := mail.Address{"", "test@example.com"}
	subj := "hello"
	body := "Hello world!"

	// Setup headers
	headers := make(map[string]string)
	headers["From"] = from.String()
	headers["To"] = to.String()
	headers["Subject"] = subj

	// Setup message
	message := ""
	for k, v := range headers {
		message += fmt.Sprintf("%s: %s\r\n", k, v)
	}
	message += "\r\n" + body

	// Connect to the SMTP Server
	smtp_host, _ := os.LookupEnv("SMTP_HOST")
	smtp_port, _ := os.LookupEnv("SMTP_PORT")
	smtp_servername := smtp_host + ":" + smtp_port
	smtp_user, _ := os.LookupEnv("SMTP_USER")
	smtp_domain, _ := os.LookupEnv("SMTP_DOMAIN")
	smtp_password, _ := os.LookupEnv("SMTP_PASSWORD")
	auth := smtp.PlainAuth("", smtp_user+"@"+smtp_domain, smtp_password, smtp_host)
	smtp_transport_security, _ := os.LookupEnv("SMTP_TRANSPORT_SECURITY")
	c, err := smtp.Dial(smtp_servername)
	defer c.Quit()
	if err != nil {
		handleError(w, err)
	}
	if smtp_transport_security == "starttls" {
		// TLS config
		tlsconfig := &tls.Config{
			InsecureSkipVerify: true,
			ServerName:         smtp_host,
		}
		c.StartTLS(tlsconfig)
	}

	// Auth
	if smtp_transport_security == "tls" {
		if err = c.Auth(auth); err != nil {
			handleError(w, err)
		}
	}

	// To && From
	if err = c.Mail(from.Address); err != nil {
		handleError(w, err)
	}

	if err = c.Rcpt(to.Address); err != nil {
		handleError(w, err)
	}

	// Data
	m, err := c.Data()
	if err != nil {
		handleError(w, err)
	}

	_, err = m.Write([]byte(message))
	if err != nil {
		handleError(w, err)
	}

	err = m.Close()
	if err != nil {
		handleError(w, err)
	}

	fmt.Fprintf(w, "Sent")

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

var tp *sdktrace.TracerProvider

// initTracer creates and registers trace provider instance.
func initTracer(ctx context.Context) error {
	exp, err := otlptracehttp.New(ctx)
	if err != nil {
		return fmt.Errorf("failed to initialize stdouttrace exporter: %w", err)
	}
	bsp := sdktrace.NewBatchSpanProcessor(exp)
	tp = sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithSpanProcessor(bsp),
	)
	otel.SetTracerProvider(tp)
	return nil
}

func main() {
	ctx := context.Background()
	// initialize trace provider.
	if err := initTracer(ctx); err != nil {
		log.Printf(err.Error())
	}

	// Create a named tracer with package path as its name.
	tracer := tp.Tracer("example.com/go-app")
	defer func() { _ = tp.Shutdown(ctx) }()
	var span trace.Span
	ctx, span = tracer.Start(ctx, "operation")
	defer span.End()
	span.AddEvent("Nice operation!", trace.WithAttributes(attribute.Int("bogons", 100)))
	if err := service.SubOperation(ctx); err != nil {
		panic(err)
	}

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
	mux.HandleFunc("/{$}", mainHandler.serveHelloWorld)
	mux.HandleFunc("/send_mail", mainHandler.serveMail)
	mux.HandleFunc("/openfga/list-authorization-models", mainHandler.serveOpenFgaListAuthorizationModels)
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
