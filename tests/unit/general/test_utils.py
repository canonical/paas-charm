# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utils unit tests."""
from unittest.mock import MagicMock

import pytest

from paas_charm.utils import build_validation_error_message


@pytest.mark.parametrize(
    "validation_error",
    [
        pytest.param(
            [{"loc": ("non-optional-test",), "msg": "Field required"}],
            id="only missing",
        ),
        pytest.param(
            [{"loc": ("application-root",), "msg": "Input should be a valid string"}],
            id="only invalid",
        ),
        pytest.param(
            [
                {
                    "loc": (),
                    "msg": "Value error, flask-secret-key-id missing 'value' key in the secret content",
                }
            ],
            id="value error",
        ),
        pytest.param(
            [
                {"loc": ("non-optional-test",), "msg": "Field required"},
                {"loc": ("application-root",), "msg": "Input should be a valid string"},
                {
                    "loc": (),
                    "msg": "Value error, flask-secret-key-id missing 'value' key in the secret content",
                },
            ],
            id="missing, invalid and value errors",
        ),
    ],
)
def test_build_validation_error_message(validation_error: list[dict]) -> None:
    """
    arrange: Provide a mock validation error.
    act: Build the validation error message.
    assert: It should return the formatted error message with the expected strings.
    """
    mock_validation_error = MagicMock()
    mock_validation_error.errors.return_value = validation_error

    output = build_validation_error_message(mock_validation_error)

    for error in validation_error:
        if "Field required" in error["msg"]:
            assert "missing" in output[0]
            assert "Field required" in output[1]
        if error["loc"]:
            assert error["loc"][0] in output[0]
            assert error["loc"][0] in output[1]
        assert error["msg"] in output[1]


def test_build_validation_error_message_only_missing() -> None:
    """
    arrange: Provide a mock validation error.
    act: Build the validation error message.
    assert: The formatted error message should not include 'invalid options'.
    """
    mock_validation_error = MagicMock()
    mock_validation_error.errors.return_value = [
        {
            "loc": ("non-optional-test",),
            "msg": "Field required",
        }
    ]

    output = build_validation_error_message(mock_validation_error)

    assert "invalid options" not in output[0]
    assert "missing" in output[0]
    assert "Field required" in output[1]


def test_build_validation_error_message_only_invalid() -> None:
    """
    arrange: Provide a mock validation error.
    act: Build the validation error message.
    assert: The formatted error message should not include 'missing options'.
    """
    mock_validation_error = MagicMock()
    mock_validation_error.errors.return_value = [
        {
            "loc": ("application-root",),
            "msg": "Input should be a valid string",
        }
    ]

    output = build_validation_error_message(mock_validation_error)

    assert "missing options" not in output[0]
    assert "missing" not in output[0]
    assert "Input should be a valid string" in output[1]
