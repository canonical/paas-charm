// Copyright 2025 Canonical Ltd.
// See LICENSE file for licensing details.

package service

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"net/url"
	"os"
	"strings"

	amqp "github.com/rabbitmq/amqp091-go"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/trace"
)

// SubOperation is an example to demonstrate the use of named tracer.
// It creates a named tracer with its package path.
func SubOperation(ctx context.Context) error {
	// Using global provider. Alternative is to have application provide a getter
	// for its component to get the instance of the provider.
	tr := otel.Tracer("example.com/go-app")

	var span trace.Span
	_, span = tr.Start(ctx, "Sub operation...")
	defer span.End()
	span.AddEvent("Sub span event")

	return nil
}

type Service struct {
	PostgresqlURL string
	RabbitMQURL   string
}

func (s *Service) CheckPostgresqlMigrateStatus() (err error) {
	db, err := sql.Open("pgx", s.PostgresqlURL)
	if err != nil {
		return
	}
	defer db.Close()

	var version string
	err = db.QueryRow("SELECT version()").Scan(&version)
	if err != nil {
		return
	}
	log.Printf("postgresql version %s.", version)

	var numUsers int
	// This will fail if the table does not exist.
	err = db.QueryRow("SELECT count(*) from USERS").Scan(&numUsers)
	if err != nil {
		return
	}
	log.Printf("Number of users in Postgresql %d.", numUsers)

	return
}

// GetRabbitMQConnectionFromURI matches the Flask get_rabbitmq_connection_from_uri logic
func (s *Service) GetRabbitMQConnectionFromURI() (*amqp.Connection, error) {
	if s.RabbitMQURL == "" {
		return nil, fmt.Errorf("RABBITMQ_CONNECT_STRING not set")
	}
	return amqp.Dial(s.RabbitMQURL)
}

// GetRabbitMQConnection handles multiple unit addresses by parsing hostnames
func (s *Service) GetRabbitMQConnection() (*amqp.Connection, error) {
	// First, attempt the primary connection string
	if s.RabbitMQURL != "" {
		log.Printf("Attempting primary connection: %s", s.RabbitMQURL)
		conn, err := amqp.Dial(s.RabbitMQURL)
		if err == nil {
			return conn, nil
		}
		log.Printf("Primary connection failed: %v", err)
	}

	// Fallback to RABBITMQ_HOSTNAMES if primary fails
	hostnames := os.Getenv("RABBITMQ_HOSTNAMES")
	if hostnames == "" {
		return nil, fmt.Errorf("no fallback hostnames available in RABBITMQ_HOSTNAMES")
	}

	// Use credentials from the primary URL or other env vars if needed
	// For this example, we assume hostnames are IPs and we reuse the URI format
	// Example format of RABBITMQ_HOSTNAMES: "10.0.0.1,10.0.0.2,10.0.0.3"
	units := strings.Split(hostnames, ",")

	// Example credentials extraction logic (simplified)
	// In a real scenario, you might store user/pass in separate variables
	user := os.Getenv("RABBITMQ_USERNAME")
	pass := os.Getenv("RABBITMQ_PASSWORD")

	for _, ip := range units {
		ip = strings.TrimSpace(ip)
		// Constructing URI for each unit
		addr := fmt.Sprintf("amqp://%s:%s@%s:5672/", user, pass, ip)

		log.Printf("Attempting to connect to fallback unit: %s", ip)
		conn, err := amqp.Dial(addr)
		if err == nil {
			log.Printf("Successfully connected to unit: %s", ip)
			return conn, nil
		}
		log.Printf("Failed to connect to unit %s: %v", ip, err)
	}

	return nil, fmt.Errorf("could not connect to any RabbitMQ units")
}

// CheckRabbitMQStatus connects to RabbitMQ and declares a test queue
func (s *Service) CheckRabbitMQStatus() error {
	conn, err := s.GetRabbitMQConnection()
	if err != nil {
		return fmt.Errorf("failed to connect to RabbitMQ: %w", err)
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		return fmt.Errorf("failed to open a channel: %w", err)
	}
	defer ch.Close()

	_, err = ch.QueueDeclare(
		"test_queue", // name
		false,        // durable
		false,        // delete when unused
		false,        // exclusive
		false,        // no-wait
		nil,          // arguments
	)
	if err != nil {
		return fmt.Errorf("failed to declare a queue: %w", err)
	}

	log.Println("Successfully connected to RabbitMQ and declared test_queue")
	return nil
}
func (s *Service) RabbitMQSend() error {
	conn, err := s.GetRabbitMQConnection()
	if err != nil {
		return err
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		return err
	}
	defer ch.Close()

	// Declare a classic, non-durable queue to match existing deployments
	q, err := ch.QueueDeclare(
		"charm",
		false, // durable
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		return err
	}

	return ch.PublishWithContext(context.Background(), "", q.Name, false, false, amqp.Publishing{
		ContentType: "text/plain",
		Body:        []byte("SUCCESS"),
	})
}

func (s *Service) RabbitMQSendToUnit(unitIndex int) error {
	hostnames := os.Getenv("RABBITMQ_HOSTNAMES")
	if hostnames == "" {
		return fmt.Errorf("RABBITMQ_HOSTNAMES not set")
	}
	units := strings.Split(hostnames, ",")
	if unitIndex < 0 || unitIndex >= len(units) {
		return fmt.Errorf("unit index %d out of range", unitIndex)
	}
	ip := strings.TrimSpace(units[unitIndex])
	if ip == "" {
		return fmt.Errorf("unit index %d has empty hostname", unitIndex)
	}

	user := os.Getenv("RABBITMQ_USERNAME")
	pass := os.Getenv("RABBITMQ_PASSWORD")
	if user == "" || pass == "" {
		return fmt.Errorf("RABBITMQ_USERNAME or RABBITMQ_PASSWORD not set")
	}

	port := os.Getenv("RABBITMQ_PORT")
	if port == "" {
		port = "5672"
	}
	vc := os.Getenv("RABBITMQ_VHOST")
	if vc == "" {
		vc = "/"
	}
	vhost := url.PathEscape(vc)
	addr := fmt.Sprintf("amqp://%s:%s@%s:%s/%s", user, pass, ip, port, vhost)

	log.Printf("Attempting to connect to unit index %d at %s", unitIndex, ip)
	conn, err := amqp.Dial(addr)
	if err != nil {
		return err
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		return err
	}
	defer ch.Close()

	q, err := ch.QueueDeclare(
		"charm",
		false,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		return err
	}

	return ch.PublishWithContext(context.Background(), "", q.Name, false, false, amqp.Publishing{
		ContentType: "text/plain",
		Body:        []byte("SUCCESS"),
	})
}

func (s *Service) RabbitMQReceive() (string, error) {
	conn, err := s.GetRabbitMQConnection()
	if err != nil {
		return "FAIL. NO CONNECTION.", err
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		return "FAIL", err
	}
	defer ch.Close()

	// basic_get in RabbitMQ (non-streaming)
	msg, ok, err := ch.Get("charm", false)
	if err != nil {
		return "FAIL", err
	}
	if !ok {
		return "FAIL. NO MESSAGE.", nil
	}

	if string(msg.Body) == "SUCCESS" {
		msg.Ack(false)
		return "SUCCESS", nil
	}

	return "FAIL. INCORRECT MESSAGE.", nil
}

func (s *Service) RabbitMQReceiveFromUnit(unitIndex int) (string, error) {
	hostnames := os.Getenv("RABBITMQ_HOSTNAMES")
	if hostnames == "" {
		return "FAIL. NO HOSTNAMES.", fmt.Errorf("RABBITMQ_HOSTNAMES not set")
	}
	units := strings.Split(hostnames, ",")
	if unitIndex < 0 || unitIndex >= len(units) {
		return "FAIL. BAD UNIT.", fmt.Errorf("unit index %d out of range", unitIndex)
	}
	ip := strings.TrimSpace(units[unitIndex])
	if ip == "" {
		return "FAIL. BAD UNIT.", fmt.Errorf("unit index %d has empty hostname", unitIndex)
	}

	user := os.Getenv("RABBITMQ_USERNAME")
	pass := os.Getenv("RABBITMQ_PASSWORD")
	if user == "" || pass == "" {
		return "FAIL. NO CREDS.", fmt.Errorf("RABBITMQ_USERNAME or RABBITMQ_PASSWORD not set")
	}

	port := os.Getenv("RABBITMQ_PORT")
	if port == "" {
		port = "5672"
	}
	vc := os.Getenv("RABBITMQ_VHOST")
	if vc == "" {
		vc = "/"
	}
	vhost := url.PathEscape(vc)
	addr := fmt.Sprintf("amqp://%s:%s@%s:%s/%s", user, pass, ip, port, vhost)

	log.Printf("Attempting to connect to unit index %d at %s", unitIndex, ip)
	conn, err := amqp.Dial(addr)
	if err != nil {
		return "FAIL. NO CONNECTION.", err
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		return "FAIL", err
	}
	defer ch.Close()

	msg, ok, err := ch.Get("charm", false)
	if err != nil {
		return "FAIL", err
	}
	if !ok {
		return "FAIL. NO MESSAGE.", nil
	}

	if string(msg.Body) == "SUCCESS" {
		msg.Ack(false)
		return "SUCCESS", nil
	}

	return "FAIL. INCORRECT MESSAGE.", nil
}
