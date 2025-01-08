// Copyright 2025 Canonical Ltd.
// See LICENSE file for licensing details.

package service

import (
	"database/sql"
	"log"
)

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
