// Copyright 2025 Canonical Ltd.
// See LICENSE file for licensing details.

package service

import (
	"context"
	"database/sql"
	"fmt"
	"log"

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

// CheckRabbitMQStatus connects to RabbitMQ and declares a test queue
func (s *Service) CheckRabbitMQStatus() error {
	conn, err := s.GetRabbitMQConnectionFromURI()
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
	conn, err := s.GetRabbitMQConnectionFromURI()
	if err != nil {
		return err
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		return err
	}
	defer ch.Close()

	q, err := ch.QueueDeclare("charm", false, false, false, false, nil)
	if err != nil {
		return err
	}

	return ch.PublishWithContext(context.Background(), "", q.Name, false, false, amqp.Publishing{
		ContentType: "text/plain",
		Body:        []byte("SUCCESS"),
	})
}

func (s *Service) RabbitMQReceive() (string, error) {
	conn, err := s.GetRabbitMQConnectionFromURI()
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
