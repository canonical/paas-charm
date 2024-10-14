# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the Databases class to handle database relations and state."""

import logging
import typing

import ops
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires

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


def make_database_requirers(
    charm: ops.CharmBase, database_name: str
) -> typing.Dict[str, DatabaseRequires]:
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
            DatabaseRequires(
                charm,
                relation_name=name,
                database_name=database_name,
            )
        )
        for name in db_interfaces
    }
    return databases


def get_uri(database_requires: DatabaseRequires) -> str | None:
    """Compute a URI for DatabaseRequires and return it.

    Args:
        database_requires: DatabaseRequires object from the data platform.

    Returns:
        uri for the database of None if the uri could not be built.
    """
    relation_data = list(
        database_requires.fetch_relation_data(
            fields=["uris", "endpoints", "username", "password", "database"]
        ).values()
    )

    if not relation_data:
        return None

    # There can be only one database integrated at a time
    # with the same interface name. See: metadata.yaml
    data = relation_data[0]

    if "uris" in data:
        return data["uris"]

    # Check that the relation data is well formed according to the following json_schema:
    # https://github.com/canonical/charm-relation-interfaces/blob/main/interfaces/mysql_client/v0/schemas/provider.json
    if not all(data.get(key) for key in ("endpoints", "username", "password")):
        logger.warning("Incorrect relation data from the data provider: %s", data)
        return None

    database_name = data.get("database", database_requires.database)
    endpoint = data["endpoints"].split(",")[0]
    return (
        f"{database_requires.relation_name}://"
        f"{data['username']}:{data['password']}"
        f"@{endpoint}/{database_name}"
    )
