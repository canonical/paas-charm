# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for CharmState in all supported frameworks."""


import nest_asyncio
import pytest
from juju.application import Application
from juju.model import Model

nest_asyncio.apply()


@pytest.mark.parametrize(
    "blocked_app_fixture, missing_configs, first_non_optional_config, rest_of_the_invalid_configs, remaining_non_optional_configs_dict",
    [
        pytest.param(
            "flask_blocked_app",
            ["non-optional-bool", "non-optional-int"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {"non-optional-int": "1"},
            id="flask",
        ),
        pytest.param(
            "django_blocked_app",
            ["non-optional-bool", "non-optional-int"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {"non-optional-int": "1"},
            id="django",
        ),
        pytest.param(
            "fastapi_blocked_app",
            ["non-optional-bool", "non-optional-int", "non-optional-string"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {"non-optional-int": "1", "non-optional-string": "non-optional-value"},
            id="fastapi",
        ),
        pytest.param(
            "go_blocked_app",
            ["non-optional-bool", "non-optional-int"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {"non-optional-int": "1"},
            id="go",
        ),
    ],
)
async def test_non_optional(
    model: Model,
    blocked_app_fixture: str,
    missing_configs: list[str],
    first_non_optional_config: dict,
    rest_of_the_invalid_configs: list[str],
    remaining_non_optional_configs_dict: dict,
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
    for missing_config in missing_configs:
        assert missing_config in blocked_app.status_message

    await blocked_app.set_config(first_non_optional_config)
    await model.wait_for_idle(apps=[blocked_app.name], status="blocked", timeout=300)
    for invalid_config in rest_of_the_invalid_configs:
        assert invalid_config in blocked_app.status_message
    for config in first_non_optional_config.keys():
        assert config not in blocked_app.status_message

    await blocked_app.set_config(remaining_non_optional_configs_dict)
    await model.wait_for_idle(apps=[blocked_app.name], status="active", timeout=300)
    for missing_config in missing_configs:
        assert missing_config not in blocked_app.status_message
