# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""


import nest_asyncio
import pytest
from juju.application import Application
from juju.model import Model

nest_asyncio.apply()


@pytest.mark.parametrize(
    "blocked_app_fixture",
    [
        "flask_blocked_app",
        "django_blocked_app",
        "fastapi_blocked_app",
        "go_blocked_app",
    ],
)
async def test_non_optional(
    model: Model,
    blocked_app_fixture: str,
    request: pytest.FixtureRequest,
):
    """
    arrange: Deploy the application.
    act: Set the non-optional config options 1 by 1 and check.
    assert: At first both options should be in status message,
        when one set the charm should still be in blocked state
        with the message showing which option is missing.
        When both set charm should be in active state.
    """
    blocked_app: Application = request.getfixturevalue(blocked_app_fixture)
    missing_configs = ["non-optional-test", "non-optional-test-1"]
    assert blocked_app.status == "blocked"
    for invalid_config in missing_configs:
        assert invalid_config in blocked_app.status_message

    await blocked_app.set_config(
        {
            "non-optional-test-1": "something",
        }
    )
    await model.wait_for_idle(apps=[blocked_app.name], status="blocked", timeout=300)
    assert "non-optional-test-1" not in blocked_app.status_message
    assert "non-optional-test" in blocked_app.status_message

    await blocked_app.set_config(
        {
            "non-optional-test": "something else",
        }
    )
    await model.wait_for_idle(apps=[blocked_app.name], status="active", timeout=300)
    for invalid_config in missing_configs:
        assert invalid_config not in blocked_app.status_message
