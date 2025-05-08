# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for CharmState in all supported frameworks."""

import jubilant
import pytest

from tests.integration.types import App


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
            ["non-optional-bool", "non-optional-int"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {"non-optional-int": "1"},
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
        pytest.param(
            "expressjs_blocked_app",
            ["non-optional-bool", "non-optional-int"],
            {"non-optional-bool": "True"},
            ["non-optional-int"],
            {"non-optional-int": "1"},
            id="expressjs",
        ),
    ],
)
def test_non_optional(
    juju: jubilant.Juju,
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
    blocked_app: App = request.getfixturevalue(blocked_app_fixture)
    status = juju.status()
    assert status.apps[blocked_app.name].units[blocked_app.name + "/0"].is_blocked
    for missing_config in missing_configs:
        assert missing_config in  status.apps[blocked_app.name].units[blocked_app.name + "/0"].workload_status.message

    juju.config(blocked_app.name, first_non_optional_config)
    
    for invalid_config in rest_of_the_invalid_configs:
        assert invalid_config  in  status.apps[blocked_app.name].units[blocked_app.name + "/0"].workload_status.message
    
    for config in first_non_optional_config.keys():
        juju.wait(
            lambda status: config not in  status.apps[blocked_app.name].units[blocked_app.name + "/0"].workload_status.message,
            timeout=300,
        )

    juju.config(blocked_app.name, remaining_non_optional_configs_dict)

    juju.wait(
        lambda status: jubilant.all_active(status, [blocked_app.name]),
        timeout=300,
    )
    for missing_config in missing_configs:
        juju.wait(
            lambda status: missing_config  not in  status.apps[blocked_app.name].units[blocked_app.name + "/0"].workload_status.message,
            timeout=300,
        )
