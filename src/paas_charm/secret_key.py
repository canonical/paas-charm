# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Manage the application secret key stored in a Juju application-owned secret."""

import secrets

import ops


class SecretKeyStorage(ops.Object):
    """Manage the charm's application secret key as a Juju application secret.

    The secret is owned by the application and located by a stable label, so no
    secret identifier needs to be stored in any relation databag.

    Attrs:
        is_ready: True if the application secret key is available.
    """

    def __init__(self, charm: ops.CharmBase, label: str):
        """Initialize the SecretKeyStorage.

        Args:
            charm: The charm object that uses the secret key.
            label: The Juju secret label used to store and locate the key.
        """
        super().__init__(parent=charm, key=label)
        self._charm = charm
        self._label = label

    def _get_secret(self) -> ops.Secret | None:
        """Return the application secret if it exists, otherwise None.

        Returns:
            The application secret, or None if it has not been created yet.
        """
        try:
            return self._charm.model.get_secret(label=self._label)
        except ops.SecretNotFoundError:
            return None

    def initialize(self) -> None:
        """Create the application secret key if it does not exist.

        Only the leader unit creates the secret. The operation is idempotent.
        """
        if not self._charm.unit.is_leader():
            return
        if self._get_secret() is not None:
            return
        self._charm.app.add_secret({"value": secrets.token_urlsafe(64)}, label=self._label)

    @property
    def is_ready(self) -> bool:
        """Return whether the application secret key is available.

        Returns:
            True if the secret key exists and can be read, False otherwise.
        """
        return self._get_secret() is not None

    def get_secret_key(self) -> str:
        """Return the application secret key value.

        Returns:
            The application secret key.

        Raises:
            RuntimeError: If the secret key has not been created yet.
        """
        secret = self._get_secret()
        if secret is None:
            raise RuntimeError("application secret key is not initialized")
        return secret.get_content(refresh=True)["value"]

    def rotate(self) -> None:
        """Generate a new application secret key value.

        Only the leader unit can rotate the secret.

        Raises:
            RuntimeError: If the secret key has not been created yet.
        """
        secret = self._get_secret()
        if secret is None:
            raise RuntimeError("application secret key is not initialized")
        secret.set_content({"value": secrets.token_urlsafe(64)})
