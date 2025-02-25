# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utils unit tests."""
from unittest.mock import MagicMock

import pytest

from paas_charm.charm_state import is_user_defined_config
from paas_charm.utils import build_validation_error_message


def _test_build_validation_error_message_parameters():
    return [
        pytest.param(
            [{"loc": ("non-optional",), "msg": "Field required"}],
            ["non-optional"],
            ["missing"],
            ["invalid", "required"],
            ["field", "required"],
            id="only missing",
        ),
        pytest.param(
            [{"loc": ("invalid-string",), "msg": "Input should be a valid string"}],
            ["invalid-string"],
            ["invalid", "option"],
            ["missing", "valid string"],
            ["valid string", "invalid"],
            id="invalid string",
        ),
        pytest.param(
            [{"loc": ("invalid-int",), "msg": "Input should be a valid int"}],
            ["invalid-int"],
            ["invalid", "option"],
            ["missing", "valid int"],
            ["valid int", "invalid"],
            id="invalid int",
        ),
        pytest.param(
            [{"loc": ("invalid-bool",), "msg": "Input should be a valid bool"}],
            ["invalid-bool"],
            ["invalid", "option"],
            ["missing", "valid bool"],
            ["valid bool", "invalid"],
            id="invalid bool",
        ),
        pytest.param(
            [{"loc": ("invalid-float",), "msg": "Input should be a valid float"}],
            ["invalid-float"],
            ["invalid", "option"],
            ["missing", "valid float"],
            ["valid float", "invalid"],
            id="invalid float",
        ),
        pytest.param(
            [
                {"loc": ("invalid-string",), "msg": "Input should be a valid string"},
                {"loc": ("invalid-int",), "msg": "Input should be a valid int"},
            ],
            ["invalid-string", "invalid-int"],
            ["invalid", "option"],
            ["missing", "valid string", "valid int"],
            ["valid string", "valid int", "invalid"],
            id="invalid string and int",
        ),
        pytest.param(
            [
                {
                    "loc": (),
                    "msg": "Value error, invalid-dict missing 'value' key in the secret content",
                }
            ],
            [],
            ["invalid", "option"],
            ["missing", "invalid-dict"],
            ["invalid-dict", "invalid", "value error"],
            id="value error",
        ),
        pytest.param(
            [
                {"loc": ("non-optional-1",), "msg": "Field required"},
                {"loc": ("non-optional-2",), "msg": "Field required"},
            ],
            ["non-optional-1", "non-optional-2"],
            ["missing"],
            ["invalid", "required"],
            ["field", "required"],
            id="2 missing",
        ),
        pytest.param(
            [
                {"loc": ("invalid-bool",), "msg": "Input should be a valid bool"},
                {"loc": ("non-optional",), "msg": "Field required"},
            ],
            ["invalid-bool", "non-optional"],
            ["missing", "invalid", "option"],
            ["valid bool", "required"],
            ["valid bool", "invalid", "required"],
            id="invalid bool, missing option",
        ),
        pytest.param(
            [
                {"loc": ("non-optional",), "msg": "Field required"},
                {"loc": ("invalid-bool",), "msg": "Input should be a valid bool"},
                {
                    "loc": (),
                    "msg": "Value error, invalid-dict missing 'value' key in the secret content",
                },
            ],
            ["invalid-bool", "non-optional"],
            ["missing", "invalid", "option"],
            ["invalid-dict", "value error", "valid bool", "required"],
            [
                "valid bool",
                "invalid",
                "required",
                "value error",
                "invalid-dict",
            ],
            id="invalid bool, value error, missing option",
        ),
        pytest.param(
            [
                {
                    "loc": (
                        "invalid-dict",
                        "invalid-bool",
                    ),
                    "msg": "Some error",
                },
            ],
            ["invalid-dict.invalid-bool"],
            ["invalid", "option"],
            ["some error"],
            [
                "invalid",
                "some error",
            ],
            id="multiple loc",
        ),
    ]


@pytest.mark.parametrize(
    "validation_error, expected_loc_strs, expected_error_message_substrs, unexpected_error_message_substr, expected_error_log_substrs",
    _test_build_validation_error_message_parameters(),
)
@pytest.mark.parametrize(
    "underscore", [pytest.param(True, id="underscore"), pytest.param(False, id="no underscore")]
)
@pytest.mark.parametrize("prefix", ["", "abc-"])
def test_build_validation_error_message(
    validation_error: list[dict],
    expected_loc_strs: list[str],
    expected_error_message_substrs: list[str],
    unexpected_error_message_substr: list[str],
    expected_error_log_substrs: list[str],
    underscore: bool,
    prefix: str,
) -> None:
    """
    arrange: Provide a mock validation error.
    act: Build the validation error message.
    assert: It should return the formatted error message with the expected strings.
    """
    mock_validation_error = MagicMock()
    mock_validation_error.errors.return_value = validation_error

    output = build_validation_error_message(
        mock_validation_error, prefix=prefix, underscore_to_dash=underscore
    )

    for substr in expected_error_message_substrs:
        assert substr in output.short.lower()

    for substr in expected_loc_strs:
        if underscore:
            assert f"{prefix}{substr}".replace("_", "-") in output.short.lower()
            assert f"{prefix}{substr}".replace("_", "-") in output.long.lower()
        else:
            assert f"{prefix}{substr}" in output.short.lower()
            assert f"{prefix}{substr}" in output.long.lower()

    for substr in unexpected_error_message_substr:
        assert substr not in output.short.lower()

    for substr in expected_error_log_substrs:
        assert substr in output.long.lower()


@pytest.mark.parametrize(
    "framework, option_name, expected_result",
    [
        pytest.param("flask", "flask-config", False),
        pytest.param("flask", "user-defined-config", True),
        pytest.param("flask", "webserver-config", False),
        pytest.param("flask", "app-config", False),
        pytest.param("go", "user-defined-config", True),
        pytest.param("go", "webserver-config", False),
        pytest.param("go", "app-config", False),
        pytest.param("django", "django-config", False),
        pytest.param("django", "user-defined-config", True),
        pytest.param("django", "webserver-config", False),
        pytest.param("django", "app-config", False),
        pytest.param("fastapi", "user-defined-config", True),
        pytest.param("fastapi", "webserver-config", False),
        pytest.param("fastapi", "app-config", False),
    ],
)
def test_is_user_defined_config(framework, option_name, expected_result) -> None:
    """
    arrange: Provide a config option name.
    act: Call the is_user_defined_config function with the config option.
    assert: The result should be equal to the expected result.
    """

    assert is_user_defined_config(option_name, framework) == expected_result
