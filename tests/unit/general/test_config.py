# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utils unit tests."""


import os
import pathlib
import unittest

import ops
import pytest
import yaml
from ops.testing import Harness
from pydantic import Field

import paas_charm
from paas_charm.charm_state import _create_config_attribute
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.utils import config_metadata


@pytest.mark.parametrize(
    "blocked_harness_fixture",
    ["flask_harness", "go_harness", "fastapi_harness", "django_harness"],
)
@pytest.mark.parametrize(
    "required_configs, expected_status_message_substrs, unexpected_status_message_substrs, expected_log_message_substrs",
    [
        pytest.param(
            [
                {
                    "optional-test-bool": {
                        "description": "A non-optional config option for testing.",
                        "type": "boolean",
                        "optional": False,
                    }
                },
            ],
            ["non-optional-bool", "missing"],
            ["invalid", "required"],
            ["invalid", "non-optional-bool", "field", "required"],
            id="blocked for bool config",
        ),
        pytest.param(
            [
                {
                    "optional-test-int": {
                        "description": "A non-optional config option for testing.",
                        "type": "int",
                        "optional": False,
                    }
                },
            ],
            ["non-optional-int", "missing"],
            ["invalid", "required"],
            ["invalid", "non-optional-int", "field", "required"],
            id="blocked for int config",
        ),
        pytest.param(
            [
                {
                    "optional-test-float": {
                        "description": "A non-optional config option for testing.",
                        "type": "float",
                        "optional": False,
                    }
                },
            ],
            ["non-optional-float", "missing"],
            ["invalid", "required"],
            ["invalid", "non-optional-float", "field", "required"],
            id="blocked for float config",
        ),
        pytest.param(
            [
                {
                    "optional-test-string": {
                        "description": "A non-optional config option for testing.",
                        "type": "string",
                        "optional": False,
                    }
                },
            ],
            ["non-optional-string", "missing"],
            ["invalid", "required"],
            ["invalid", "non-optional-string", "field", "required"],
            id="blocked for string config",
        ),
        pytest.param(
            [
                {
                    "optional-test-secret": {
                        "description": "A non-optional config option for testing.",
                        "type": "secret",
                        "optional": False,
                    }
                },
            ],
            ["non-optional-secret", "missing"],
            ["invalid", "required"],
            ["invalid", "non-optional-secret", "field", "required"],
            id="blocked for secret config",
        ),
        pytest.param(
            [
                {
                    "optional-test-bool": {
                        "description": "A non-optional config option for testing.",
                        "type": "boolean",
                        "optional": False,
                    }
                },
                {
                    "optional-test-int": {
                        "description": "A non-optional config option for testing.",
                        "type": "int",
                        "optional": False,
                    }
                },
                {
                    "optional-test-float": {
                        "description": "A non-optional config option for testing.",
                        "type": "float",
                        "optional": False,
                    }
                },
                {
                    "optional-test-string": {
                        "description": "A non-optional config option for testing.",
                        "type": "string",
                        "optional": False,
                    }
                },
                {
                    "optional-test-secret": {
                        "description": "A non-optional config option for testing.",
                        "type": "secret",
                        "optional": False,
                    }
                },
            ],
            [
                "non-optional-bool",
                "non-optional-int",
                "non-optional-float",
                "non-optional-string",
                "non-optional-secret",
            ],
            ["invalid", "required"],
            [
                "invalid",
                "non-optional-bool",
                "non-optional-int",
                "non-optional-float",
                "non-optional-string",
                "non-optional-secret",
                "field",
                "required",
            ],
            id="blocked for multiple configs",
        ),
    ],
)
def test_non_optional_config(
    request,
    blocked_harness_fixture: Harness,
    required_configs: list[dict],
    expected_status_message_substrs: list[str],
    unexpected_status_message_substrs: list[str],
    expected_log_message_substrs: list[str],
    monkeypatch,
) -> None:
    """
    arrange: Deploy charm with fake config options in charmcraft.yaml.
    act: Try to create charm state.
    assert: The charm should be in blocked state with correct message and logs.
    """
    blocked_harness = request.getfixturevalue(blocked_harness_fixture)

    charm_dir = pathlib.Path(os.getcwd())
    config_file = charm_dir / "charmcraft.yaml"
    if config_file.exists():
        yaml_dict = yaml.safe_load(config_file.read_text())
    for config in required_configs:
        yaml_dict["config"]["options"].update(config)
    monkeypatch.setattr(
        paas_charm.charm_state,
        "config_metadata",
        unittest.mock.MagicMock(return_value=yaml_dict["config"]),
    )
    blocked_harness.begin_with_initial_hooks()
    with pytest.raises(CharmConfigInvalidError) as exc:
        blocked_harness.charm._create_charm_state()
        assert isinstance(blocked_harness.model.unit.status, ops.model.BlockedStatus)
        for substr in expected_log_message_substrs:
            assert substr in str(exc).lower()
        for substr in expected_status_message_substrs:
            assert substr in str(blocked_harness.model.unit.status.message).lower()
        for substr in unexpected_status_message_substrs:
            assert substr not in str(blocked_harness.model.unit.status.message).lower()


@pytest.mark.parametrize(
    "parametrized_harness_fixture, prefix",
    [
        ["flask_harness", "flask"],
        ["go_harness", "app"],
        ["fastapi_harness", "app"],
        ["django_harness", "django"],
    ],
)
def test_get_framework_config_with_prefix(
    parametrized_harness_fixture: str, prefix: str, request
) -> None:
    """
    arrange: Get the config options with framework related prefix.
    act: Start the charm and get the framework config object
    assert: Framework config object should have the framework related prefixed config options as attributes.
    """
    harness = request.getfixturevalue(parametrized_harness_fixture)
    harness.begin()
    metadata = config_metadata(pathlib.Path(os.getcwd()))
    framework_keys = [
        option[6:].replace("-", "_") for option in metadata["options"] if option.startswith(prefix)
    ]

    framework_config = harness.charm.get_framework_config()

    assert list(framework_config.__annotations__.keys()).sort() == framework_keys.sort()


@pytest.mark.parametrize(
    "parametrized_harness_fixture, secret_key, expected_status_message_substrs, unexpected_status_message_substrs, expected_log_message_substrs",
    [
        pytest.param(
            "flask_harness",
            "flask-secret-key",
            ["invalid", "config", "flask-secret-key"],
            ["valid string"],
            ["invalid", "config", "flask-secret-key", "valid string"],
        ),
        pytest.param(
            "go_harness",
            "app-secret-key",
            ["invalid", "config", "app-secret-key"],
            ["valid string"],
            ["invalid", "config", "app-secret-key", "valid string"],
        ),
        pytest.param(
            "fastapi_harness",
            "app-secret-key",
            ["invalid", "config", "app-secret-key"],
            ["valid string"],
            ["invalid", "config", "app-secret-key", "valid string"],
        ),
        pytest.param(
            "django_harness",
            "django-secret-key",
            ["invalid", "config", "django-secret-key"],
            ["valid string"],
            ["invalid", "config", "django-secret-key", "valid string"],
        ),
    ],
)
def test_get_framework_config_invalid(
    parametrized_harness_fixture: str,
    secret_key: str,
    expected_status_message_substrs: list[str],
    unexpected_status_message_substrs: list[str],
    expected_log_message_substrs: list[str],
    request,
) -> None:
    """
    arrange: Get the charm.
    act: Set a config option to empty string.
    assert: Charm should raise a CharmConfigInvalidError.
    """
    harness = request.getfixturevalue(parametrized_harness_fixture)
    harness.begin()
    harness.update_config({secret_key: ""})

    with pytest.raises(CharmConfigInvalidError) as exc:
        framework_config = harness.charm.get_framework_config()
        for substr in expected_log_message_substrs:
            assert substr in str(exc).lower()
        for substr in expected_status_message_substrs:
            assert substr in str(harness.model.unit.status.message).lower()
        for substr in unexpected_status_message_substrs:
            assert substr not in str(harness.model.unit.status.message).lower()


def _test_app_config_parameters():
    non_optional_options = [
        {
            "name": (config_name_1 := "non_optional_bool"),
            "type_dict": {"type": "boolean", "optional": False},
            "type_result": (config_name_1, (bool, Field())),
        },
        {
            "name": (config_name_2 := "non_optional_int"),
            "type_dict": {"type": "int", "optional": False},
            "type_result": (config_name_2, (int, Field())),
        },
        {
            "name": (config_name_3 := "non_optional_float"),
            "type_dict": {"type": "float", "optional": False},
            "type_result": (config_name_3, (float, Field())),
        },
        {
            "name": (config_name_4 := "non_optional_str"),
            "type_dict": {"type": "string", "optional": False},
            "type_result": (config_name_4, (str, Field())),
        },
        {
            "name": (config_name_5 := "non_optional_secret"),
            "type_dict": {"type": "secret", "optional": False},
            "type_result": (config_name_5, (dict, Field())),
        },
    ]
    explicit_optional_options = [
        {
            "name": (config_name := f"explicit{option['name'][3:]}"),
            "type_dict": {"type": option["type_dict"]["type"], "optional": True},
            "type_result": (config_name, (option["type_result"][1][0] | None, None)),
        }
        for option in non_optional_options
    ]
    implicit_optional_options = [
        {
            "name": (config_name := f"implicit{option['name'][3:]}"),
            "type_dict": {"type": option["type_dict"]["type"]},
            "type_result": (config_name, (option["type_result"][1][0] | None, None)),
        }
        for option in non_optional_options
    ]

    all_options = implicit_optional_options + explicit_optional_options + non_optional_options
    return [
        pytest.param(option["name"], option["type_dict"], option["type_result"], id=option["name"])
        for option in all_options
    ]


@pytest.mark.parametrize(
    "option_name, option_dict, expected_output", _test_app_config_parameters()
)
def test_app_config(option_name, option_dict, expected_output):
    """
    arrange: Provide dictionaries for optional and non optional config options.
    act: Create an attribute.
    assert: The resultant attribute should have the correct type.
    """
    assert repr(_create_config_attribute(option_name, option_dict)) == repr(expected_output)


def _test_app_config_class_factory_parameters():
    mock_yaml = {
        "options": {
            (config_name_1 := "bool"): {"type": "boolean", "optional": False},
            (config_name_2 := "optional-bool"): {"type": "boolean", "optional": True},
            (config_name_3 := "int"): {"type": "int", "optional": False},
            (config_name_4 := "optional-int"): {"type": "int", "optional": True},
            (config_name_5 := "float"): {"type": "float", "optional": False},
            (config_name_6 := "optional-float"): {"type": "float", "optional": True},
            (config_name_7 := "str"): {"type": "string", "optional": False},
            (config_name_8 := "optional-str"): {"type": "string", "optional": True},
            (config_name_9 := "secret"): {"type": "secret", "optional": False},
            (config_name_10 := "optional-secret"): {"type": "secret", "optional": True},
            (config_name_12 := "webserver-option"): {"type": "string"},
            (config_name_13 := "app-option"): {"type": "string"},
        }
    }
    expected_output = {
        config_name_1: bool,
        config_name_2.replace("-", "_"): bool | None,
        config_name_3: int,
        config_name_4.replace("-", "_"): int | None,
        config_name_5: float,
        config_name_6.replace("-", "_"): float | None,
        config_name_7: str,
        config_name_8.replace("-", "_"): str | None,
        config_name_9: dict,
        config_name_10.replace("-", "_"): dict | None,
    }
    return [
        pytest.param(mock_yaml, expected_output),
    ]


@pytest.mark.parametrize("mock_yaml, expected_output", _test_app_config_class_factory_parameters())
@pytest.mark.parametrize("framework", ["flask", "go", "fastapi", "django"])
def test_app_config_class_factory(
    mock_yaml: dict, expected_output: dict, framework: str, monkeypatch
):
    """
    arrange: Provide mock config yaml with optional and non optional config options.
    act: Create an AppConfig object.
    assert: The resultant AppConfig object should have the required parameters set correctly.
        The AppConfig object should not have attributes for framework settings.
    """
    monkeypatch.setattr(
        "paas_charm.charm_state.config_metadata",
        unittest.mock.MagicMock(return_value=mock_yaml),
    )

    assert (
        paas_charm.charm_state.app_config_class_factory(framework).__annotations__
        == expected_output
    )
