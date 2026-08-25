# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scenario-style unit tests for FastAPIApp structured logging integration."""

import pytest
from ops import testing

from paas_charm.paas_config import LoggingFormat, PaasConfig

_LOG_CONFIG_DIR = "/tmp/fastapi/log_config"
_HANDLER_FILE = "uvicorn_log_handler.py"
_CONFIG_FILE = "uvicorn-log-config.json"


@pytest.mark.parametrize(
    "fastapi_context, expected, absent",
    [
        pytest.param(
            PaasConfig(framework_logging_format=LoggingFormat.NONE),
            [],
            ["UVICORN_LOG_CONFIG", "PYTHONPATH"],
            id="no-json-logging",
        ),
        pytest.param(
            PaasConfig(framework_logging_format=LoggingFormat.JSON),
            ["UVICORN_LOG_CONFIG", "PYTHONPATH"],
            [],
            id="json-logging-enabled",
        ),
    ],
    indirect=["fastapi_context"],
)
def test_fastapi_logging_environment(
    fastapi_context,
    base_state,
    expected: list[str],
    absent: list[str],
) -> None:
    """
    arrange: set framework_logging_format in paas-config.yaml (or leave it unset).
    act: run pebble-ready.
    assert: UVICORN_LOG_CONFIG / PYTHONPATH are present (or absent) as expected.
    """
    state = testing.State(**base_state)
    container = state.get_container("app")
    state_out = fastapi_context.run(
        fastapi_context.on.pebble_ready(container=container),
        state,
    )

    plan = state_out.get_container("app").plan
    env = plan.services["fastapi"].environment if plan and "fastapi" in plan.services else {}

    for key in expected:
        assert key in env, f"Expected env var {key!r} missing"
    for key in absent:
        assert key not in env, f"Unexpected env var {key!r} present"

    if "UVICORN_LOG_CONFIG" in expected:
        assert env["UVICORN_LOG_CONFIG"] == f"{_LOG_CONFIG_DIR}/{_CONFIG_FILE}"
        assert env["PYTHONPATH"].startswith(_LOG_CONFIG_DIR)


def test_fastapi_json_logging_files_pushed(
    fastapi_context,
    base_state,
) -> None:
    """
    arrange: use the real FastAPI paas-config with framework_logging_format=json.
    act: run pebble-ready.
    assert: formatter and log-config files are pushed to /tmp/fastapi/log_config/ in the container.
    """
    state = testing.State(**base_state)
    container = state.get_container("app")
    state_out = fastapi_context.run(
        fastapi_context.on.pebble_ready(container=container),
        state,
    )

    container_out = state_out.get_container("app")
    fs = container_out.get_filesystem(fastapi_context)
    assert (
        fs / _LOG_CONFIG_DIR.lstrip("/") / _HANDLER_FILE
    ).exists(), f"{_HANDLER_FILE} not pushed"
    assert (fs / _LOG_CONFIG_DIR.lstrip("/") / _CONFIG_FILE).exists(), f"{_CONFIG_FILE} not pushed"


@pytest.mark.parametrize(
    "fastapi_context",
    [PaasConfig(framework_logging_format=LoggingFormat.NONE)],
    indirect=True,
)
def test_fastapi_no_files_pushed_without_json_logging(
    fastapi_context,
    base_state,
) -> None:
    """
    arrange: no framework_logging_format set (default).
    act: run pebble-ready.
    assert: /tmp/fastapi/log_config/ is not created in the container.
    """
    state = testing.State(**base_state)
    container = state.get_container("app")
    state_out = fastapi_context.run(
        fastapi_context.on.pebble_ready(container=container),
        state,
    )

    container_out = state_out.get_container("app")
    fs = container_out.get_filesystem(fastapi_context)
    assert not (
        fs / _LOG_CONFIG_DIR.lstrip("/")
    ).exists(), "/tmp/fastapi/log_config should not be created"
