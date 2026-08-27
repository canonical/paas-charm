# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Test charm and custom relation classes for the CustomRelation API tests."""

import ops

from paas_charm.exceptions import InvalidRelationDataError
from paas_charm.relations import CustomRelation
from tests.unit.test_charm.src.charm import TestCharm

# Module-level call recorders reset by the test suite before each scenario.
reconcile_calls: list[str] = []
setup_calls: list[str] = []


class ExampleDbRelation(CustomRelation):
    """Env-var custom relation exposing an ``EXAMPLE_DB_URI`` variable."""

    relation_name = "example-db"

    def setup(self, on_change) -> None:
        """Observe relation events and forward them to the framework reconcile."""
        setup_calls.append(self.relation_name)
        self._framework_observe(
            self.charm.on["example-db"].relation_changed,
            on_change,
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
        """Return the ``EXAMPLE_DB_URI`` environment variable."""
        relation = self.charm.model.get_relation("example-db")
        if not relation or not relation.app:
            return {}
        bag = relation.data[relation.app]
        uri = bag.get("uri")
        if not uri:
            raise InvalidRelationDataError("missing 'uri'", relation=self.relation_name)
        return {"EXAMPLE_DB_URI": uri}


class ContextRelation(CustomRelation):
    """Custom relation that exposes the injected :class:`Context` as env vars."""

    relation_name = "example-db"

    def setup(self, on_change) -> None:
        """Record that setup ran with an ``on_change`` callback."""
        setup_calls.append(self.relation_name)
        if not callable(on_change):
            raise AssertionError("on_change callback was not injected into setup()")

    def is_ready(self) -> bool:
        """Always ready for the context inspection test."""
        return True

    def gen_environment(self) -> dict[str, str]:
        """Expose the :class:`Context` fields as environment variables."""
        ctx = self.context
        return {
            "CTX_APP_NAME": ctx.app_name,
            "CTX_FRAMEWORK": ctx.framework_name,
            "CTX_PORT": str(ctx.port),
            "CTX_CONTAINER": ctx.container_name,
        }


class InvalidDataRelation(CustomRelation):
    """Custom relation that raises on malformed relation data."""

    relation_name = "invalid-db"

    def setup(self, on_change) -> None:
        """Record setup."""
        setup_calls.append(self.relation_name)

    def is_ready(self) -> bool:
        """Raise ``InvalidRelationDataError`` when data is present but malformed."""
        relation = self.charm.model.get_relation("invalid-db")
        if not relation or not relation.app:
            return False
        if "uri" not in relation.data[relation.app]:
            raise InvalidRelationDataError("missing 'uri'", relation=self.relation_name)
        return True

    def gen_environment(self) -> dict[str, str]:
        """No environment variables."""
        return {}


class OverwritingRelation(CustomRelation):
    """Custom relation that overwrites a built-in environment variable."""

    relation_name = "example-db"

    def setup(self, on_change) -> None:
        """Record setup."""
        setup_calls.append(self.relation_name)

    def is_ready(self) -> bool:
        """Always ready."""
        return True

    def gen_environment(self) -> dict[str, str]:
        """Return a mapping that collides with the built-in ``APP_SECRET_KEY``."""
        return {"APP_SECRET_KEY": "overwritten-by-custom"}


class NginxRouteRelation(CustomRelation):
    """Side-effect custom relation with no env vars."""

    relation_name = "nginx-route"

    def setup(self, on_change) -> None:
        """Record setup."""
        setup_calls.append(self.relation_name)

    def reconcile(self) -> None:
        """Record that the side-effect reconcile ran."""
        reconcile_calls.append(self.relation_name)


class EnvVarCharm(TestCharm):
    """Test charm wiring the env-var custom relation."""

    custom_relations = [ExampleDbRelation]


class ContextCharm(TestCharm):
    """Test charm wiring the context inspection custom relation."""

    custom_relations = [ContextRelation]


class InvalidDataCharm(TestCharm):
    """Test charm wiring the invalid-data custom relation."""

    custom_relations = [InvalidDataRelation]


class OverwritingCharm(TestCharm):
    """Test charm wiring the overwriting custom relation."""

    custom_relations = [OverwritingRelation]


class SideEffectCharm(TestCharm):
    """Test charm wiring the side-effect custom relation."""

    custom_relations = [NginxRouteRelation]


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(EnvVarCharm)
