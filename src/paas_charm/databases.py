# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the Databases class to handle database relations and state."""

import logging
import typing

import ops
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from pydantic import BaseModel

SUPPORTED_DB_INTERFACES = {
    "mysql_client": "mysql",
    "postgresql_client": "postgresql",
    "mongodb_client": "mongodb",
}

logger = logging.getLogger(__name__)


class Application(typing.Protocol):  # pylint: disable=too-few-public-methods
    """Interface for the charm managed application."""

    def restart(self) -> None:
        """Restart the application."""


class PaaSDatabaseRelationData(BaseModel):
    """Data model for database relation data.

    Attributes:
        uris: A commat separated list of URIs for the database.
    """

    uris: str


class PaaSDatabaseRequires(DatabaseRequires):  # pylint: disable=too-many-ancestors
    """Class to handle database relations."""

    def to_relation_data(self) -> PaaSDatabaseRelationData | None:
        """Convert the current state to relation data.

        Returns:
            DatabaseRelationData: The relation data if available, None otherwise.
        """
        relation_data = list(
            self.fetch_relation_data(
                fields=["uris", "endpoints", "username", "password", "database"]
            ).values()
        )

        if not relation_data:
            return None

        # There can be only one database integrated at a time
        # with the same interface name. See: metadata.yaml
        data = relation_data[0]

        if "uris" in data:
            return PaaSDatabaseRelationData(uris=data["uris"])

        # Check that the relation data is well formed according to the following json_schema:
        # https://github.com/canonical/charm-relation-interfaces/blob/main/interfaces/mysql_client/v0/schemas/provider.json
        if not all(data.get(key) for key in ("endpoints", "username", "password")):
            logger.warning("Incorrect relation data from the data provider: %s", data)
            return None

        database_name = data.get("database", self.database)
        endpoint = data["endpoints"].split(",")[0]
        return PaaSDatabaseRelationData(
            uris=f"{self.relation_name}://"
            f"{data['username']}:{data['password']}"
            f"@{endpoint}/{database_name}"
        )


def make_database_requirers(
    charm: ops.CharmBase, database_name: str
) -> typing.Dict[str, PaaSDatabaseRequires]:
    """Create database requirer objects for the charm.

    Args:
        charm: The requiring charm.
        database_name: the required database name

    Returns: A dictionary which is the database uri environment variable name and the
        value is the corresponding database requirer object.
    """
    db_interfaces = (
        SUPPORTED_DB_INTERFACES[require.interface_name]
        for require in charm.framework.meta.requires.values()
        if require.interface_name in SUPPORTED_DB_INTERFACES
    )
    # automatically create database relation requirers to manage database relations
    # one database relation requirer is required for each of the database relations
    # create a dictionary to hold the requirers
    databases = {
        name: (
            PaaSDatabaseRequires(
                charm,
                relation_name=name,
                database_name=database_name,
            )
        )
        for name in db_interfaces
    }
    return databases
