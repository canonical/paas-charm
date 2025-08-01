// Copyright 2025 Canonical Ltd.
// See LICENSE file for licensing details.

package main

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"go-app/internal/service"
	"io"
	"log"
	"net/http"
	"net/mail"
	"net/smtp"
	"net/url"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

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

	"github.com/gorilla/sessions"
	"github.com/markbates/goth"
	"github.com/markbates/goth/gothic"
	"github.com/markbates/goth/providers/openidConnect"
)

// OIDC-specific constants for the session store
const (
	maxAge      = 86400 * 30 // 30 days
	SessionName = "_user_session"
)

// Config holds all application configuration, read once from the environment.
type Config struct {
	BaseURL     string
	BasePath    string
	LoginURL    string
	Provider    string
	Port        string
	MetricsPort string
	MetricsPath string
}

// NewConfig creates a new Config struct from environment variables.
func NewConfig() (Config, error) {
	baseURLStr := os.Getenv("APP_BASE_URL")
	if baseURLStr == "" {
		return Config{}, errors.New("APP_BASE_URL environment variable must be set")
	}

	baseURL, err := url.Parse(baseURLStr)
	if err != nil {
		return Config{}, fmt.Errorf("invalid APP_BASE_URL: %w", err)
	}

	basePath := baseURL.Path
	if basePath == "" {
		basePath = "/"
	}

	provider := "openid-connect" // Default provider name for goth

	port, found := os.LookupEnv("APP_PORT")
	if !found {
		port = "8080"
	}
	metricsPort, found := os.LookupEnv("APP_METRICS_PORT")
	if !found {
		metricsPort = "8081"
	}
	metricsPath, found := os.LookupEnv("APP_METRICS_PATH")
	if !found {
		metricsPath = "/metrics"
	}

	return Config{
		BaseURL:     strings.TrimSuffix(baseURLStr, "/"),
		BasePath:    basePath,
		Provider:    provider,
		LoginURL:    fmt.Sprintf("%s/login/%s", strings.TrimSuffix(baseURLStr, "/"), provider),
		Port:        port,
		MetricsPort: metricsPort,
		MetricsPath: metricsPath,
	}, nil
}

type mainHandler struct {
	counter prometheus.Counter
	service service.Service
	config  Config
	store   sessions.Store
}

// serveHelloWorld now acts as the main landing page with a login link.
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

	from := mail.Address{Name: "", Address: "tester@example.com"}
	to := mail.Address{Name: "", Address: "test@example.com"}
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

// OIDC-specific: callback handler now shows the user data directly.
func (h mainHandler) serveAuthCallback(w http.ResponseWriter, r *http.Request) {
	user, err := gothic.CompleteUserAuth(w, r)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	session, err := h.store.New(r, SessionName)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	userMap := map[string]string{
		"email":    user.Email,
		"provider": user.Provider,
	}

	userData, err := json.Marshal(userMap)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	session.Values["user"] = userData
	err = h.store.Save(r, w, session)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	profileURL := h.config.BaseURL + "/profile"
	w.Header().Set("Location", profileURL)
	w.WriteHeader(http.StatusTemporaryRedirect)
}

// OIDC-specific: logout handler
func (h mainHandler) serveLogout(w http.ResponseWriter, r *http.Request) {
	gothic.Logout(w, r)
	session, err := h.store.New(r, SessionName)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Set MaxAge to -1. This effectively deletes the cookie.
	session.Options.MaxAge = -1
	err = h.store.Save(r, w, session)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	homeURL := h.config.BaseURL
	if homeURL == "" {
		homeURL = "/"
	}
	w.Header().Set("Location", homeURL)
	w.WriteHeader(http.StatusTemporaryRedirect)
}

func (h mainHandler) serveProfile(w http.ResponseWriter, r *http.Request) {
	session, err := h.store.Get(r, SessionName)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	userData, ok := session.Values["user"]
	if !ok {
		http.Error(w, "User not authenticated.", http.StatusForbidden)
		return
	}

	userDataBytes, ok := userData.([]byte)
	if !ok {
		http.Error(w, "User data in session is of unexpected type", http.StatusInternalServerError)
		return
	}

	var userMap map[string]interface{}
	err = json.Unmarshal(userDataBytes, &userMap)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	logoutURL := fmt.Sprintf("%s/logout/%s", h.config.BaseURL, userMap["provider"])

	fmt.Fprintf(w, `<!DOCTYPE html>
<html>
<head>
    <title>Profile</title>
    <style>
        body { font-family: sans-serif; margin: 2em; background-color: #f4f4f9; color: #333; }
        h1 { color: #0056b3; }
        pre { background-color: #eef; padding: 1em; border-radius: 5px; border: 1px solid #ddd; white-space: pre-wrap; word-wrap: break-word; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Welcome, %s!</h1>
    <p><a href="%s">Logout</a></p>
    <h2>Your OIDC Data:</h2>
    <pre>%s</pre>
</body>
</html>`, userMap["email"].(string), logoutURL, userMap)
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
	// Load all configuration from environment variables at startup.
	config, err := NewConfig()
	if err != nil {
		log.Fatalf("Configuration error: %v", err)
	}

	// OIDC-specific: setup gothic session store
	key, found := os.LookupEnv("APP_SECRET_KEY")
	if !found || key == "" {
		log.Fatal("APP_SECRET_KEY environment variable must be set.")
	}
	store := sessions.NewCookieStore([]byte(key))
	store.MaxAge(maxAge)
	store.Options.Path = config.BasePath
	store.Options.HttpOnly = true
	gothic.Store = store

	log.Printf("Session cookie configured with Path: %s and Secure: %t and SameSite: %d", store.Options.Path, store.Options.Secure, store.Options.SameSite)

	// Do not do this in production!
	// This disables SSL verification.
	http.DefaultTransport.(*http.Transport).TLSClientConfig = &tls.Config{InsecureSkipVerify: true}

	// Construct the full redirect URL.
	redirectPath := os.Getenv("APP_OIDC_REDIRECT_PATH")
	if redirectPath == "" {
		log.Fatal("APP_OIDC_REDIRECT_PATH environment variable must be set")
	}
	redirectURL := config.BaseURL + redirectPath
	log.Println("Using Redirect URL:", redirectURL)

	// OIDC-specific: setup the openid-connect provider
	oidcProvider, err := openidConnect.NewCustomisedURL(
		os.Getenv("APP_OIDC_CLIENT_ID"),
		os.Getenv("APP_OIDC_CLIENT_SECRET"),
		redirectURL,
		os.Getenv("APP_OIDC_AUTHORIZE_URL"),
		os.Getenv("APP_OIDC_ACCESS_TOKEN_URL"),
		os.Getenv("APP_OIDC_API_BASE_URL"),
		os.Getenv("APP_OIDC_USER_URL"),
		"", // endSessionEndpointURL
		strings.Split(os.Getenv("APP_OIDC_SCOPES"), " ")...,
	)
	if err != nil {
		log.Fatalf("Failed to create OIDC provider: %v", err)
	}

	goth.UseProviders(oidcProvider)
	log.Println("Registered OIDC provider:", oidcProvider.Name())

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
		config:  config,
		store:   store,
	}
	mux.HandleFunc("/{$}", mainHandler.serveHelloWorld)
	mux.HandleFunc("/send_mail", mainHandler.serveMail)
	mux.HandleFunc("/openfga/list-authorization-models", mainHandler.serveOpenFgaListAuthorizationModels)
	mux.HandleFunc("/env/user-defined-config", mainHandler.serveUserDefinedConfig)
	mux.HandleFunc("/postgresql/migratestatus", mainHandler.servePostgresql)

	// OIDC-specific: Add OIDC routes
	mux.HandleFunc("/auth/{provider}/callback", mainHandler.serveAuthCallback)
	mux.HandleFunc("/logout/{provider}", mainHandler.serveLogout)
	mux.HandleFunc("/login/{provider}", func(w http.ResponseWriter, r *http.Request) {
		gothic.BeginAuthHandler(w, r)
	})
	mux.HandleFunc("/profile", mainHandler.serveProfile)

	if config.MetricsPort != config.Port {
		prometheus.MustRegister(requestCounter)

		prometheusMux := http.NewServeMux()
		prometheusMux.Handle(config.MetricsPath, promhttp.Handler())
		prometheusServer := &http.Server{
			Addr:    ":" + config.MetricsPort,
			Handler: prometheusMux,
		}
		go func() {
			if err := prometheusServer.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
				log.Fatalf("Prometheus HTTP server error: %v", err)
			}
			log.Println("Prometheus HTTP Stopped serving new connections.")
		}()
	} else {
		mux.Handle(config.MetricsPath, promhttp.Handler())
	}

	server := &http.Server{
		Addr:    ":" + config.Port,
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
