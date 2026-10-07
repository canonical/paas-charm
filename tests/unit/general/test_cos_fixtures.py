# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Regression tests for COS integration fixture waits."""

import importlib
import itertools
import json
from unittest.mock import MagicMock

import pytest


@pytest.fixture(name="cos_fixtures")
def cos_fixtures_loader():
    """Load COS fixtures when the existing integration dependencies are installed."""
    jubilant = pytest.importorskip("jubilant")
    pytest.importorskip("minio")
    pytest.importorskip("opcli")
    fixtures = importlib.import_module("tests.integration.integrations.conftest")
    return jubilant, fixtures


@pytest.mark.parametrize("final_status", ["active", "error", "blocked"])
@pytest.mark.parametrize(
    "fixture_module",
    ["tests.integration.conftest", "tests.integration.integrations.conftest"],
)
def test_loki_waits_for_recovery_or_fails_boundedly(
    monkeypatch, cos_fixtures, final_status, fixture_module
):
    """Both Loki fixtures allow recovery but fail on hook errors or persistent blocked states."""
    jubilant, _ = cos_fixtures
    fixtures = importlib.import_module(fixture_module)
    deploy = fixtures.deploy_loki_fixture.__wrapped__
    juju = jubilant.Juju(wait_timeout=1)
    states = iter(["blocked", "blocked", "waiting"])
    calls = []

    def cli(*args, **kwargs):
        calls.append(args)
        assert args[0] == "status"
        current = next(states, final_status)
        return (
            json.dumps(
                {
                    "model": {
                        "name": "testing",
                        "type": "caas",
                        "controller": "controller",
                        "cloud": "k8s",
                        "version": "3.6.29",
                    },
                    "machines": {},
                    "applications": {
                        "loki-k8s": {
                            "charm": "loki-k8s",
                            "charm-origin": "charmhub",
                            "charm-name": "loki-k8s",
                            "charm-rev": 199,
                            "exposed": False,
                            "application-status": {"current": current},
                        }
                    },
                }
            ),
            "",
        )

    clock = itertools.count()
    monkeypatch.setattr(juju, "_cli", cli)
    monkeypatch.setattr("jubilant._juju.time.monotonic", lambda: next(clock) / 10)
    monkeypatch.setattr("jubilant._juju.time.sleep", lambda delay: None)

    if final_status == "active":
        assert deploy(juju, "loki-k8s").name == "loki-k8s"
        assert len(calls) == 6
    else:
        error = jubilant.WaitError if final_status == "error" else TimeoutError
        with pytest.raises(error):
            deploy(juju, "loki-k8s")
        if final_status == "error":
            assert len(calls) == 4


@pytest.mark.parametrize("app_name", ["loki-k8s", "prometheus-k8s"])
@pytest.mark.parametrize("current", ["blocked", "error"])
def test_prometheus_wait_allows_transient_blocks_but_not_errors(cos_fixtures, app_name, current):
    """Prometheus startup tolerates blocked states but still fails on any app or unit error."""
    _, fixtures = cos_fixtures
    juju = MagicMock()
    juju.status.return_value.apps = {"prometheus-k8s": MagicMock()}
    assert fixtures.deploy_prometheus_fixture.__wrapped__(juju, "prometheus-k8s").name == (
        "prometheus-k8s"
    )
    status = MagicMock()
    status.apps = {}
    for name in ("loki-k8s", "prometheus-k8s"):
        app = MagicMock()
        app.app_status.current = current if name == app_name else "active"
        app.units = {}
        app.is_active = app.app_status.current == "active"
        status.apps[name] = app

    ready = juju.wait.call_args.args[0]
    error = juju.wait.call_args.kwargs["error"]
    assert ready(status) == (app_name == "loki-k8s")
    assert error(status) == (current == "error")
    assert juju.wait.call_args.kwargs["timeout"] == 6 * 60
