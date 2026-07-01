# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for CustomIntegration API (IntegrationHandle-based)."""

import unittest
from unittest.mock import MagicMock, PropertyMock, call

import ops

from paas_charm.integrations import CustomIntegration, IntegrationHandle, OnChange
from paas_charm.exceptions import InvalidRelationDataError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_handle(*, config: dict | None = None, on_change=None) -> IntegrationHandle:
    """Build an IntegrationHandle backed by MagicMock objects."""
    charm = MagicMock(spec=ops.CharmBase)
    charm.model = MagicMock()
    charm.app = MagicMock()
    charm.unit = MagicMock()
    charm.on = MagicMock()
    charm.framework = MagicMock()
    charm.framework.observe = MagicMock()
    if on_change is None:
        on_change = MagicMock()
    return IntegrationHandle(
        charm=charm,
        config=config or {},
        on_change=on_change,
    )


# ---------------------------------------------------------------------------
# IntegrationHandle tests
# ---------------------------------------------------------------------------

class TestIntegrationHandle(unittest.TestCase):
    """Tests for IntegrationHandle passthrough properties."""

    def setUp(self):
        self.handle = make_handle(config={"webserver-port": 8080})

    def test_charm_property(self):
        """handle.charm returns the CharmBase instance."""
        self.assertIsInstance(self.handle.charm, MagicMock)

    def test_config_property(self):
        """handle.config returns the merged config dict."""
        self.assertEqual(self.handle.config["webserver-port"], 8080)

    def test_on_change_property(self):
        """handle.on_change is the callback."""
        self.assertTrue(callable(self.handle.on_change))

    def test_model_shortcut(self):
        """handle.model is handle.charm.model."""
        self.assertIs(self.handle.model, self.handle.charm.model)

    def test_app_shortcut(self):
        """handle.app is handle.charm.app."""
        self.assertIs(self.handle.app, self.handle.charm.app)

    def test_unit_shortcut(self):
        """handle.unit is handle.charm.unit."""
        self.assertIs(self.handle.unit, self.handle.charm.unit)

    def test_on_shortcut(self):
        """handle.on is handle.charm.on."""
        self.assertIs(self.handle.on, self.handle.charm.on)

    def test_observe_shortcut(self):
        """handle.observe is handle.charm.framework.observe."""
        self.assertIs(self.handle.observe, self.handle.charm.framework.observe)

    def test_on_change_is_callable(self):
        """handle.on_change can be called with and without rerun_migrations."""
        mock_fn = MagicMock()
        h = make_handle(on_change=mock_fn)
        h.on_change()
        h.on_change(rerun_migrations=True)
        mock_fn.assert_has_calls([
            call(),
            call(rerun_migrations=True),
        ])


# ---------------------------------------------------------------------------
# CustomIntegration defaults
# ---------------------------------------------------------------------------

class ConcreteMinimal(CustomIntegration):
    """Minimal concrete subclass — only setup() is required."""
    relation_name = "test-rel"

    def setup(self, handle: IntegrationHandle) -> None:
        self.handle = handle


class TestCustomIntegrationDefaults(unittest.TestCase):
    """Tests for the default implementations on CustomIntegration."""

    def setUp(self):
        self.integration = ConcreteMinimal()
        self.handle = make_handle()
        self.integration.setup(self.handle)

    def test_relation_data_default_none(self):
        """Default relation_data() returns None."""
        self.assertIsNone(self.integration.relation_data())

    def test_is_ready_default_false_when_no_data(self):
        """Default is_ready() returns False when relation_data() is None."""
        self.assertFalse(self.integration.is_ready())

    def test_gen_environment_default_empty(self):
        """Default gen_environment() returns {}."""
        self.assertEqual(self.integration.gen_environment(None), {})

    def test_reconcile_default_noop(self):
        """Default reconcile() does nothing."""
        self.integration.reconcile(self.handle)  # must not raise

    def test_setup_stores_handle(self):
        """setup() receives and can store IntegrationHandle."""
        self.assertIs(self.integration.handle, self.handle)


# ---------------------------------------------------------------------------
# Env-var integration pattern
# ---------------------------------------------------------------------------

class ConcreteEnvVar(CustomIntegration):
    """Env-var integration: reads a URI from the relation bag."""
    relation_name = "example-db"

    def setup(self, handle: IntegrationHandle) -> None:
        self._handle = handle
        handle.observe(
            handle.on["example-db"].relation_changed,
            lambda _: handle.on_change(rerun_migrations=True),
        )
        handle.observe(
            handle.on["example-db"].relation_broken,
            lambda _: handle.on_change(),
        )

    def relation_data(self):
        relation = self._handle.model.get_relation("example-db")
        if not relation or not relation.app:
            return None
        uri = relation.data[relation.app].get("uri")
        if relation.data[relation.app] and not uri:
            raise InvalidRelationDataError("missing 'uri'", relation=self.relation_name)
        return uri

    def gen_environment(self, relation_data):
        return {"EXAMPLE_DB_URI": relation_data}


class TestEnvVarIntegration(unittest.TestCase):
    """Tests for the env-var integration pattern."""

    def setUp(self):
        self.integration = ConcreteEnvVar()
        self.handle = make_handle()
        self.integration.setup(self.handle)

    def test_setup_calls_observe(self):
        """setup() calls handle.observe for each event."""
        self.assertEqual(self.handle.observe.call_count, 2)

    def test_relation_data_returns_none_when_no_relation(self):
        """relation_data() returns None when no relation exists."""
        self.handle.model.get_relation.return_value = None
        self.assertIsNone(self.integration.relation_data())

    def test_relation_data_returns_none_when_no_app(self):
        """relation_data() returns None when relation.app is None."""
        mock_relation = MagicMock()
        mock_relation.app = None
        self.handle.model.get_relation.return_value = mock_relation
        self.assertIsNone(self.integration.relation_data())

    def test_relation_data_returns_uri(self):
        """relation_data() returns the URI from the databag."""
        mock_relation = MagicMock()
        mock_relation.app = MagicMock()
        mock_relation.data = {mock_relation.app: {"uri": "postgresql://host/db"}}
        self.handle.model.get_relation.return_value = mock_relation
        self.assertEqual(self.integration.relation_data(), "postgresql://host/db")

    def test_relation_data_raises_on_missing_uri(self):
        """relation_data() raises InvalidRelationDataError when bag is present but uri absent."""
        mock_relation = MagicMock()
        mock_relation.app = MagicMock()
        mock_relation.data = {mock_relation.app: {"other_key": "value"}}
        self.handle.model.get_relation.return_value = mock_relation
        with self.assertRaises(InvalidRelationDataError):
            self.integration.relation_data()

    def test_is_ready_true_when_data(self):
        """is_ready() returns True when relation_data() is not None."""
        mock_relation = MagicMock()
        mock_relation.app = MagicMock()
        mock_relation.data = {mock_relation.app: {"uri": "postgresql://host/db"}}
        self.handle.model.get_relation.return_value = mock_relation
        self.assertTrue(self.integration.is_ready())

    def test_is_ready_false_when_no_data(self):
        """is_ready() returns False when relation_data() is None."""
        self.handle.model.get_relation.return_value = None
        self.assertFalse(self.integration.is_ready())

    def test_gen_environment_maps_uri(self):
        """gen_environment() maps the URI to EXAMPLE_DB_URI."""
        env = self.integration.gen_environment("postgresql://host/db")
        self.assertEqual(env, {"EXAMPLE_DB_URI": "postgresql://host/db"})


# ---------------------------------------------------------------------------
# Side-effect integration pattern
# ---------------------------------------------------------------------------

class ConcreteSideEffect(CustomIntegration):
    """Side-effect integration: never blocks, reconcile writes a file."""
    relation_name = "nginx-route"

    def setup(self, handle: IntegrationHandle) -> None:
        self._handle = handle
        self._setup_called_with = handle

    def is_ready(self) -> bool:
        return True

    def reconcile(self, handle: IntegrationHandle) -> None:
        self._reconcile_called_with = handle


class TestSideEffectIntegration(unittest.TestCase):
    """Tests for the side-effect integration pattern."""

    def setUp(self):
        self.integration = ConcreteSideEffect()
        self.handle = make_handle()
        self.integration.setup(self.handle)

    def test_is_ready_always_true(self):
        """Side-effect integration is_ready() returns True unconditionally."""
        self.assertTrue(self.integration.is_ready())

    def test_relation_data_default_none(self):
        """relation_data() still returns None for side-effect integrations."""
        self.assertIsNone(self.integration.relation_data())

    def test_gen_environment_default_empty(self):
        """gen_environment() still returns {} for side-effect integrations."""
        self.assertEqual(self.integration.gen_environment(None), {})

    def test_reconcile_called_with_handle(self):
        """reconcile() receives the IntegrationHandle."""
        self.integration.reconcile(self.handle)
        self.assertIs(self.integration._reconcile_called_with, self.handle)

    def test_setup_receives_handle(self):
        """setup() receives the IntegrationHandle."""
        self.assertIs(self.integration._setup_called_with, self.handle)


# ---------------------------------------------------------------------------
# OnChange protocol
# ---------------------------------------------------------------------------

class TestOnChangeProtocol(unittest.TestCase):
    """Tests for the OnChange protocol contract."""

    def test_restart_satisfies_protocol(self):
        """A function accepting rerun_migrations=False satisfies OnChange."""
        calls = []

        def my_restart(*, rerun_migrations: bool = False) -> None:
            calls.append(rerun_migrations)

        handle = make_handle(on_change=my_restart)
        handle.on_change()
        handle.on_change(rerun_migrations=True)
        self.assertEqual(calls, [False, True])


if __name__ == "__main__":
    unittest.main()
