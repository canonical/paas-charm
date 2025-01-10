# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the DatabaseMigration class to manage database migrations."""
import enum
import logging
import pathlib
from typing import cast

import ops
from ops.pebble import ExecError

from paas_charm.exceptions import CharmConfigInvalidError

logger = logging.getLogger(__name__)


class DatabaseMigrationStatus(str, enum.Enum):
    """Database migration status.

    Attrs:
        COMPLETED: A status denoting a successful database migration.
        FAILED: A status denoting an unsuccessful database migration.
        PENDING: A status denoting a pending database migration.
    """

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class DatabaseMigration:
    """The DatabaseMigration class that manages database migrations."""

    def __init__(
        self,
        container: ops.Container,
        state_dir: pathlib.Path,
    ):
        """Initialize the DatabaseMigration instance.

        Args:
            container: The application container object.
            state_dir: the directory in the application container to store migration states.
        """
        self._container = container
        self._status_file = state_dir / "database-migration-status"
        self._completed_script_file = state_dir / "completed-database-migration"

    def get_status(self) -> DatabaseMigrationStatus:
        """Get the database migration run status.

        Returns:
            One of "PENDING", "COMPLETED", or "FAILED".
        """
        return (
            DatabaseMigrationStatus.PENDING
            if not self._container.can_connect() or not self._container.exists(self._status_file)
            else DatabaseMigrationStatus(cast(str, self._container.pull(self._status_file).read()))
        )

    def set_status_to_pending(self) -> None:
        """Set the database migration run status to pending."""
        self._set_status(DatabaseMigrationStatus.PENDING)

    def _set_status(self, status: DatabaseMigrationStatus) -> None:
        """Set the database migration run status.

        Args:
            status: One of "PENDING", "COMPLETED", or "FAILED".
        """
        self._container.push(self._status_file, source=status, make_dirs=True)

    # disable the too-many-arguments check because it's a wrapper around `ops.Container.exec`
    # pylint: disable=too-many-arguments
    def run(
        self,
        *,
        command: list[str],
        environment: dict[str, str],
        working_dir: pathlib.Path,
        user: str | None = None,
        group: str | None = None,
    ) -> None:
        """Run the database migration script if database migration is still pending.

        Args:
            command: The database migration command to run.
            environment: Environment variables that's required for the run.
            working_dir: Working directory for the database migration run.
            user: The user to run the database migration.
            group: The group to run the database migration.

        Raises:
            CharmConfigInvalidError: if the database migration run failed.
        """
        if self.get_status() not in (
            DatabaseMigrationStatus.PENDING,
            DatabaseMigrationStatus.FAILED,
        ):
            return
        logger.info("execute database migration command: %s", command)
        try:
            stdout, stderr = self._container.exec(
                command,
                environment=environment,
                working_dir=str(working_dir),
                user=user,
                group=group,
            ).wait_output()
            self._set_status(DatabaseMigrationStatus.COMPLETED)
            logger.info(
                "database migration command %s completed, stdout: %s, stderr: %s",
                command,
                stdout,
                stderr,
            )
        except ExecError as exc:
            self._set_status(DatabaseMigrationStatus.FAILED)
            logger.error(
                "database migration command %s failed, stdout: %s, stderr: %s",
                command,
                exc.stdout,
                exc.stderr,
            )
            raise CharmConfigInvalidError(
                f"database migration command {command} failed, will retry in next update-status"
            ) from exc
