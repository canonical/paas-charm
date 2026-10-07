# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for safe, failure-only integration diagnostics."""

import base64
import importlib
import itertools
import json
import logging
import runpy
import subprocess
from pathlib import Path
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest

from tests.integration import diagnostics


@pytest.fixture(name="loki_fixture")
def loki_fixture_loader():
    """Load the Loki fixture when the existing integration dependencies are installed."""
    jubilant = pytest.importorskip("jubilant")
    pytest.importorskip("minio")
    pytest.importorskip("opcli")
    fixtures = importlib.import_module("tests.integration.integrations.conftest")
    return jubilant, fixtures.deploy_loki_fixture.__wrapped__


@pytest.mark.parametrize("backend", ["k8s", "microk8s", "kubectl"])
def test_diagnostics_select_safe_pod_fields(monkeypatch, caplog, backend):
    """Only selected Kubernetes metadata is logged, never pod environments or JWTs."""
    jwt = "eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjEyMzQ1Njc4OTB9.signature"
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["timeout"] == 15
        assert kwargs["check"]
        if "pods" in command and command[-1] == "name":
            output = "pod/loki-k8s-0\n"
        elif "pods" in command:
            output = "loki-k8s-0 pod-uid node loki-k8s Running now true 1 3600 kubernetes"
        elif "journalctl" in command:
            output = f"Unable to authenticate the request: {jwt}"
        else:
            output = "diagnostic-result"
        return subprocess.CompletedProcess(command, 0, stdout=output)

    monkeypatch.setattr(
        diagnostics.shutil, "which", lambda name: name if name == backend else None
    )
    monkeypatch.setattr(diagnostics.subprocess, "run", run)
    with caplog.at_level(logging.INFO):
        diagnostics.collect_loki_diagnostics("testing", "loki-k8s")

    assert "loki-k8s-0 pod-uid node loki-k8s" in caplog.text
    assert jwt not in caplog.text
    assert "<redacted JWT>" in caplog.text
    query = next(command for command in calls if "pods" in command)
    expected_prefix = ["kubectl"] if backend == "kubectl" else ["sudo", "-n", backend, "kubectl"]
    assert query[: len(expected_prefix)] == expected_prefix
    columns = query[-1]
    assert "RESTARTS:.status.containerStatuses[*].restartCount" in columns
    assert "DELETING:.metadata.deletionTimestamp" in columns
    assert "REVISION:.metadata.labels.controller-revision-hash" in columns
    assert "TERMINATED:.status.containerStatuses[*].state.terminated.reason" in columns
    assert "serviceAccountToken.expirationSeconds" in columns
    assert "env" not in columns
    assert "annotations" not in columns
    assert not any(command[-1] == "json" for command in calls)
    rollout = next(command for command in calls if "statefulsets" in command)
    assert "CURRENT:.status.currentRevision" in rollout[-1]
    assert "UPDATE:.status.updateRevision" in rollout[-1]
    probe = next(command for command in calls if "exec" in command)
    assert probe[probe.index("-c") + 1] == "charm"
    assert probe[-2:] == ["testing", "loki-k8s"]
    assert all("secrets" not in command for command in calls)


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(),
        subprocess.TimeoutExpired("kubectl", 15, output="private-output"),
        subprocess.CalledProcessError(1, "kubectl", output="private-output"),
    ],
)
def test_diagnostic_commands_fail_explicitly_without_leaking_output(monkeypatch, caplog, error):
    """Expected diagnostic failures are logged and do not propagate or leak partial output."""
    run = MagicMock(side_effect=error)
    monkeypatch.setattr(diagnostics.subprocess, "run", run)
    diagnostics.collect_loki_diagnostics("testing", "loki-k8s")
    assert "unavailable" in caplog.text
    assert "private-output" not in caplog.text


def test_no_pods_skips_probe_but_collects_authentication_logs(monkeypatch, caplog):
    """An absent pod does not cause a probe error or skip independent diagnostics."""
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    monkeypatch.setattr(
        diagnostics.subprocess,
        "run",
        run,
    )
    with caplog.at_level(logging.INFO):
        diagnostics.collect_loki_diagnostics("testing", "loki-k8s")
    assert "Loki pod count: 0" in caplog.text
    assert not any("exec" in command for command in commands)
    assert any("journalctl" in command for command in commands)


def test_pod_probes_are_bounded(monkeypatch):
    """Diagnostics probe at most three pods and use bare pod names in event selectors."""
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="\n".join(f"pod/loki-k8s-{index}" for index in range(5)),
        )

    monkeypatch.setattr(diagnostics.subprocess, "run", run)
    diagnostics.collect_loki_diagnostics("testing", "loki-k8s")
    probes = [command for command in commands if "exec" in command]
    assert len(probes) == 3
    assert probes[0][probes[0].index("exec") + 1] == "loki-k8s-0"
    events = next(command for command in commands if "events" in command)
    assert "involvedObject.name=loki-k8s-0,involvedObject.kind=Pod" in events


@pytest.mark.parametrize("api_status", [200, 401, 403])
def test_token_probe_reports_metadata_not_credentials(monkeypatch, capsys, tmp_path, api_status):
    """The in-container script reads the mounted token but only emits selected metadata."""
    claims = {
        "aud": ["kubernetes"],
        "exp": 1234567890,
        "iat": 1234567000,
        "sub": "private-subject",
    }
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    token = f"header.{payload}.private-signature"
    script = tmp_path / "token_probe.py"
    script.write_text(diagnostics._TOKEN_DIAGNOSTICS)
    token_file = MagicMock()
    token_file.__enter__.return_value.read.return_value = token
    monkeypatch.setattr(Path, "open", lambda self: token_file)
    monkeypatch.setattr("os.fstat", lambda fd: MagicMock(st_ino=123, st_mtime=456))
    monkeypatch.setattr("sys.argv", ["probe", "testing", "loki-k8s"])
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.setattr("ssl.create_default_context", lambda **kwargs: None)
    response = MagicMock()
    response.__enter__.return_value.status = api_status
    opener = MagicMock(
        return_value=response,
        side_effect=(
            HTTPError("https://api", api_status, "failure", {}, None)
            if api_status != 200
            else None
        ),
    )
    monkeypatch.setattr("urllib.request.urlopen", opener)
    runpy.run_path(str(script))
    output = capsys.readouterr().out
    assert token not in output
    assert "private-subject" not in output
    assert "private-signature" not in output
    records = [json.loads(line) for line in output.splitlines()]
    assert records[0]["token_metadata"] == {
        key: claims.get(key) for key in ("iat", "nbf", "exp", "aud")
    }
    assert records[0]["token_inode"] == 123
    assert records[1] == {"mounted_token_api_status": api_status}
    request = opener.call_args.args[0]
    assert request.get_header("Authorization") == f"Bearer {token}"
    assert request.full_url.endswith("/namespaces/testing/statefulsets/loki-k8s")
    assert opener.call_args.kwargs["timeout"] == 5


@pytest.mark.parametrize("failure", ["error", "timeout"])
def test_loki_failure_collects_diagnostics_and_preserves_error(monkeypatch, loki_fixture, failure):
    """A failed Loki wait collects diagnostics once and re-raises the same error."""
    juju = MagicMock()
    juju.status.return_value.model.name = "testing"
    juju.status.return_value.apps = {}
    jubilant, deploy = loki_fixture
    error = jubilant.WaitError("error") if failure == "error" else TimeoutError("timeout")
    juju.wait.side_effect = error
    collect = MagicMock()
    monkeypatch.setattr(
        "tests.integration.integrations.conftest.collect_loki_diagnostics", collect
    )
    with pytest.raises(type(error)) as raised:
        deploy(juju, "loki-k8s")
    assert raised.value is error
    collect.assert_called_once_with("testing", "loki-k8s")


def test_successful_loki_wait_does_not_collect_diagnostics(monkeypatch, loki_fixture):
    """Successful deployments incur no diagnostic subprocess calls."""
    juju = MagicMock()
    juju.status.return_value.apps = {}
    collect = MagicMock()
    monkeypatch.setattr(
        "tests.integration.integrations.conftest.collect_loki_diagnostics", collect
    )
    _, deploy = loki_fixture
    assert deploy(juju, "loki-k8s").name == "loki-k8s"
    collect.assert_not_called()


@pytest.mark.parametrize("final_status", ["active", "error", "blocked"])
def test_loki_rollout_waits_for_recovery_or_fails_boundedly(
    monkeypatch, loki_fixture, final_status
):
    """Transient blocks recover, hook errors fail immediately, and persistent blocks time out."""
    jubilant, deploy = loki_fixture
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
    collect = MagicMock()
    monkeypatch.setattr(
        "tests.integration.integrations.conftest.collect_loki_diagnostics", collect
    )

    if final_status == "active":
        assert deploy(juju, "loki-k8s").name == "loki-k8s"
        assert len(calls) == 6
        collect.assert_not_called()
    else:
        error = jubilant.WaitError if final_status == "error" else TimeoutError
        with pytest.raises(error):
            deploy(juju, "loki-k8s")
        if final_status == "error":
            assert len(calls) == 4
        collect.assert_called_once_with("testing", "loki-k8s")
