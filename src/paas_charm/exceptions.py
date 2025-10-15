# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions used by charms."""


class CharmConfigInvalidError(Exception):
    """Exception raised when a charm configuration is found to be invalid.

    Attrs:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the CharmConfigInvalidError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class PebbleNotReadyError(Exception):
    """Exception raised when accessing pebble while it isn't ready."""


class MissingCharmLibraryError(Exception):
    """Raised when a required charm library is missing."""


class RelationDataError(Exception):
    """Raised when relation data is either unavailable, invalid or not usable.

    Attrs:
        relation: The name of the relation with error.
    """

    relation: str | None = None

    def __init__(self, message: str, relation: str | None = None):
        """Initialize a new instance of the RelationDataError exception.

        Args:
            message: Explanation of the error.
            relation: The name of the relation with error.

        Raises:
            ValueError: If relation is not provided or defined on the class.
        """
        self.relation = relation or getattr(self, "relation", None)
        if not self.relation:
            raise ValueError(f"{self.__class__.__name__} requires a 'relation' to be set.")
        super().__init__(message)


class InvalidRelationDataError(RelationDataError):
    """Raised when a relation data is invalid."""
