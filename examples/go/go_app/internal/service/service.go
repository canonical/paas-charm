// Copyright 2025 Canonical Ltd.
// See LICENSE file for licensing details.

package service

import (
	"database/sql"
	"log"

	"context"

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
