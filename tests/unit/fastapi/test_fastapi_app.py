# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scenario-style unit tests for FastAPIApp structured logging integration."""

import pathlib

import pytest
from ops import pebble, testing

from examples.fastapi.charm.src.charm import FastAPICharm
from paas_charm.paas_config import LoggingFormat

from .constants import DEFAULT_LAYER, FASTAPI_CONTAINER_NAME

_LOG_CONFIG_DIR = "/tmp/fastapi/log_config"
_HANDLER_FILE = "uvicorn_log_handler.py"
_CONFIG_FILE = "uvicorn-log-config.json"


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture() -> testing.State:
    """Return a minimal State with the app container connected and peer relation initialised."""
    container = testing.Container(
        name=FASTAPI_CONTAINER_NAME,
        can_connect=True,
        layers={"base": pebble.Layer(DEFAULT_LAYER)},
        service_statuses={"fastapi": pebble.ServiceStatus.INACTIVE},
    )
    peer_rel = testing.PeerRelation(
        "secret-storage",
        local_app_data={"fastapi_secret_key": "test-secret-key"},
    )
    return testing.State(
        containers=[container],
        relations=[peer_rel],
        leader=True,
        config={"non-optional-string": "test-value"},
    )


@pytest.mark.parametrize(
    "logging_format, expected, absent",
    [
        pytest.param(
            LoggingFormat.NONE, [], ["UVICORN_LOG_CONFIG", "PYTHONPATH"], id="no-json-logging"
        ),
        pytest.param(
            LoggingFormat.JSON,
            ["UVICORN_LOG_CONFIG", "PYTHONPATH"],
            [],
            id="json-logging-enabled",
        ),
    ],
)
def test_fastapi_logging_environment(
    base_state: testing.State,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    logging_format: LoggingFormat,
    expected: list[str],
    absent: list[str],
) -> None:
    """
    arrange: set framework_logging_format in paas-config.yaml (or leave it unset).
    act: run pebble-ready.
    assert: UVICORN_LOG_CONFIG / PYTHONPATH are present (or absent) as expected.
    """
    monkeypatch.chdir(tmp_path)
    if logging_format != LoggingFormat.NONE:
        (tmp_path / "paas-config.yaml").write_text(
            f"framework_logging_format: {logging_format.value}\n", encoding="utf-8"
        )

    ctx = testing.Context(FastAPICharm)
    container = base_state.get_container(FASTAPI_CONTAINER_NAME)
    state_out = ctx.run(ctx.on.pebble_ready(container=container), base_state)

    plan = state_out.get_container(FASTAPI_CONTAINER_NAME).plan
    env = plan.services["fastapi"].environment if plan and "fastapi" in plan.services else {}

    for key in expected:
        assert key in env, f"Expected env var {key!r} missing"
    for key in absent:
        assert key not in env, f"Unexpected env var {key!r} present"

    if logging_format == LoggingFormat.JSON:
        assert env["UVICORN_LOG_CONFIG"] == f"{_LOG_CONFIG_DIR}/{_CONFIG_FILE}"
        assert env["PYTHONPATH"].startswith(_LOG_CONFIG_DIR)


def test_fastapi_json_logging_files_pushed(
    base_state: testing.State,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """
    arrange: set framework_logging_format=json.
    act: run pebble-ready.
    assert: formatter and log-config files are pushed to /tmp/fastapi/log_config/ in the container.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "paas-config.yaml").write_text(
        "framework_logging_format: json\n", encoding="utf-8"
    )

    ctx = testing.Context(FastAPICharm)
    container = base_state.get_container(FASTAPI_CONTAINER_NAME)
    state_out = ctx.run(ctx.on.pebble_ready(container=container), base_state)

    container_out = state_out.get_container(FASTAPI_CONTAINER_NAME)
    fs = container_out.get_filesystem(ctx)
    assert (
        fs / _LOG_CONFIG_DIR.lstrip("/") / _HANDLER_FILE
    ).exists(), f"{_HANDLER_FILE} not pushed"
    assert (fs / _LOG_CONFIG_DIR.lstrip("/") / _CONFIG_FILE).exists(), f"{_CONFIG_FILE} not pushed"


def test_fastapi_no_files_pushed_without_json_logging(
    base_state: testing.State,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    """
    arrange: no framework_logging_format set (default).
    act: run pebble-ready.
    assert: /tmp/fastapi/log_config/ is not created in the container.
    """
    monkeypatch.chdir(tmp_path)

    ctx = testing.Context(FastAPICharm)
    container = base_state.get_container(FASTAPI_CONTAINER_NAME)
    state_out = ctx.run(ctx.on.pebble_ready(container=container), base_state)

    container_out = state_out.get_container(FASTAPI_CONTAINER_NAME)
    fs = container_out.get_filesystem(ctx)
    assert not (
        fs / _LOG_CONFIG_DIR.lstrip("/")
    ).exists(), "/tmp/fastapi/log_config should not be created"
