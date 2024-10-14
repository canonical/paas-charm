# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Provide the SecretStorage for managing the persistent secret storage for charms."""
import abc
import secrets
import typing

import ops


class SecretStorage(ops.Object, abc.ABC):
    """A class that manages secret keys required for charms.

    Attrs:
        is_initialized: True if the SecretStorage has been initialized.
    """

    def __init__(
        self, charm: ops.CharmBase, keys: list[str], peer_relation_name: str = "secret-storage"
    ):
        """Initialize the SecretStorage with a given Charm object.

        Args:
            charm: The charm object that uses the SecretStorage.
            keys: possible keys of secret values to be stored in the secret storage.
            peer_relation_name: the name of the peer relation to be used to store secrets.
        """
        super().__init__(parent=charm, key=peer_relation_name)
        self._charm = charm
        self._keys = keys
        self._peer_relation_name = peer_relation_name
        charm.framework.observe(
            self._charm.on[self._peer_relation_name].relation_created,
            self._on_secret_storage_relation_created,
        )

    @abc.abstractmethod
    def gen_initial_value(self) -> dict[str, str]:
        """Generate the initial secret values."""

    def _on_secret_storage_relation_created(self, event: ops.RelationEvent) -> None:
        """Handle the event when a new peer relation is created.

        Generates a new secret key and stores it within the relation's data.

        Args:
            event: The event that triggered this handler.
        """
        if not self._charm.unit.is_leader():
            return
        relation_data = event.relation.data[self._charm.app]
        initial_value: dict[str, str] = {}
        for key in self._keys:
            if not relation_data.get(key):
                if not initial_value:
                    initial_value = self.gen_initial_value()
                relation_data[key] = initial_value[key]

    @property
    def is_initialized(self) -> bool:
        """Check if the SecretStorage has been initialized.

        It's an error to read or write the secret storage before initialization.

        Returns:
            True if SecretStorage is initialized, False otherwise.
        """
        relation = self._charm.model.get_relation(self._peer_relation_name)
        if relation is None:
            return False
        relation_data = relation.data[self._charm.app]
        return all(relation_data.get(k) for k in self._keys)

    def set_secret(self, key: str, value: str) -> None:
        """Set the secret value in the relation data.

        Args:
            key: the secret value key.
            value: the secret value.

        Raises:
            RuntimeError: If SecretStorage is not initialized.
        """
        if not self.is_initialized:
            raise RuntimeError("SecretStorage is not initialized")
        relation = typing.cast(
            ops.Relation, self._charm.model.get_relation(self._peer_relation_name)
        )
        relation.data[self._charm.app][key] = value

    def get_secret(self, key: str) -> str:
        """Retrieve the secret value from the relation data.

        Args:
            key: the secret value key.

        Returns:
            The value of the associated key in the relation data.

        Raises:
            RuntimeError: If SecretStorage is not initialized.
        """
        if not self.is_initialized:
            raise RuntimeError("SecretStorage is not initialized")
        relation = typing.cast(
            ops.Relation, self._charm.model.get_relation(self._peer_relation_name)
        )
        return relation.data[self._charm.app][key]


class KeySecretStorage(SecretStorage):
    """A class that manages secret keys with one default secret key."""

    def gen_initial_value(self) -> dict[str, str]:
        """Generate the initial secret values.

        Returns:
            The initial secret values.
        """
        return {self._key: secrets.token_urlsafe(64)}

    def __init__(self, charm: ops.CharmBase, key: str):
        """Initialize the SecretStorage with a given charm object.

        Args:
            charm: The charm object that uses the SecretStorage.
            key: The secret key name stored in the relation data.
        """
        super().__init__(charm=charm, keys=[key])
        self._key = key

    def get_secret_key(self) -> str:
        """Retrieve the application secret key from the peer relation data.

        Returns:
            The application secret key.
        """
        return self.get_secret(self._key)

    def reset_secret_key(self) -> None:
        """Generate a new application secret key and store it within the peer relation data."""
        self.set_secret(self._key, secrets.token_urlsafe(64))
