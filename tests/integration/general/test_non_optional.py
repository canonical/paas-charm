# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for Flask workers and schedulers."""


import nest_asyncio
import pytest
from juju.application import Application
from juju.model import Model

nest_asyncio.apply()


@pytest.mark.parametrize(
    "blocked_app_fixture, missing_configs, set_first_configs, rest_of_the_configs, set_the_rest_of_configs",
    [
        pytest.param(
            "flask_blocked_app",
            ["non-optional-bool", "non-optional-int"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {
                "non-optional-int": "1",
            },
            id="flask",
        ),
        pytest.param(
            "django_blocked_app",
            ["non-optional-bool", "non-optional-int"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {
                "non-optional-int": "1",
            },
            id="django",
        ),
        pytest.param(
            "fastapi_blocked_app",
            ["non-optional-bool", "non-optional-int", "non-optional-string"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {"non-optional-int": "1", "non-optional-string": "something"},
            id="fastapi",
        ),
        pytest.param(
            "go_blocked_app",
            ["non-optional-bool", "non-optional-int"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {
                "non-optional-int": "1",
            },
            id="go",
        ),
    ],
)
async def test_non_optional(
    model: Model,
    blocked_app_fixture: str,
    missing_configs: list[str],
    set_first_configs: dict,
    rest_of_the_configs: list[str],
    set_the_rest_of_configs: dict,
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
    assert blocked_app.status == "blocked"
    for invalid_config in missing_configs:
        assert invalid_config in blocked_app.status_message

    await blocked_app.set_config(set_first_configs)
    await model.wait_for_idle(apps=[blocked_app.name], status="blocked", timeout=300)
    for invalid_config in rest_of_the_configs:
        assert invalid_config in blocked_app.status_message
    for config in set_first_configs.keys():
        assert config not in blocked_app.status_message

    await blocked_app.set_config(set_the_rest_of_configs)
    await model.wait_for_idle(apps=[blocked_app.name], status="active", timeout=300)
    for invalid_config in missing_configs:
        assert invalid_config not in blocked_app.status_message
