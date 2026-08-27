#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask Charm service."""

import logging
import typing

import ops

import paas_charm.flask
from paas_charm.relations import CustomRelation

logger = logging.getLogger(__name__)


class ExampleDbRelation(CustomRelation):
    """Custom env-var relation exposing an ``EXAMPLE_DB_URI`` environment variable.

    The relation reads a ``uri`` field from the remote application databag and
    contributes it to the workload environment as ``EXAMPLE_DB_URI``. It is
    declared as ``optional: True`` in ``charmcraft.yaml``, so a missing
    relation does not block the workload.
    """

    relation_name = "example-db"

    def setup(self, on_change) -> None:
        """Observe relation events and forward them to the framework reconcile.

        A new/changed endpoint re-runs migrations against the new database;
        a broken endpoint just reconciles.
        """
        self._framework_observe(
            self.charm.on["example-db"].relation_changed,
            on_change,
            True,
        )
        self._framework_observe(
            self.charm.on["example-db"].relation_broken,
            on_change,
        )

    def is_ready(self) -> bool:
        """Return True when a related app publishes a ``uri``."""
        relation = self.charm.model.get_relation("example-db")
        if not relation or not relation.app:
            return False
        return bool(relation.data[relation.app].get("uri"))

    def gen_environment(self) -> dict[str, str]:
        """Return the ``EXAMPLE_DB_URI`` environment variable.

        Raises:
            InvalidRelationDataError: when the relation bag is present but has no ``uri``.
        """
        relation = self.charm.model.get_relation("example-db")
        if not relation or not relation.app:
            return {}
        bag = relation.data[relation.app]
        uri = bag.get("uri")
        if not uri:
            raise InvalidRelationDataError("missing 'uri'", relation=self.relation_name)
        return {"EXAMPLE_DB_URI": uri}


class FlaskCharm(paas_charm.flask.Charm):
    """Flask Charm service."""

    custom_relations = [ExampleDbRelation]

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(FlaskCharm)
