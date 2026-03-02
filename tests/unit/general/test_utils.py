# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utils unit tests."""

import pathlib
from unittest.mock import MagicMock

import pytest
from ops import RelationMeta, RelationRole

from paas_charm.charm_state import is_user_defined_config
from paas_charm.exceptions import InvalidCustomCOSDirectoryError
from paas_charm.utils import (
    build_k8s_unit_fqdn,
    build_validation_error_message,
    get_endpoints_by_interface_name,
    merge_cos_directories,
    validate_cos_custom_dir,
)


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
        pytest.param("expressjs", "user-defined-config", True),
        pytest.param("expressjs", "webserver-config", False),
        pytest.param("expressjs", "app-config", False),
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


@pytest.mark.parametrize(
    "requires, interface_name, expected_relation_list",
    [
        pytest.param(
            {},
            "redis",
            [],
            id="0 relation",
        ),
        pytest.param(
            {
                "db": RelationMeta(
                    role=RelationRole.requires,
                    relation_name="db",
                    raw={"interface": "postgresql", "limit": 1},
                ),
                "cache": (
                    cache_relation := RelationMeta(
                        role=RelationRole.requires,
                        relation_name="cache",
                        raw={"interface": "redis", "limit": 1},
                    )
                ),
                "oauth": RelationMeta(
                    role=RelationRole.requires,
                    relation_name="oauth",
                    raw={"interface": "oauth", "limit": 1},
                ),
            },
            "redis",
            [("cache", cache_relation)],
            id="1 relation",
        ),
        pytest.param(
            {
                "db": RelationMeta(
                    role=RelationRole.requires,
                    relation_name="db",
                    raw={"interface": "postgresql", "limit": 1},
                ),
                "cache": (
                    cache_relation := RelationMeta(
                        role=RelationRole.requires,
                        relation_name="cache",
                        raw={"interface": "redis", "limit": 1},
                    )
                ),
                "second_cache": (
                    second_cache_relation := RelationMeta(
                        role=RelationRole.requires,
                        relation_name="second_cache",
                        raw={"interface": "redis", "limit": 1},
                    )
                ),
                "oauth": RelationMeta(
                    role=RelationRole.requires,
                    relation_name="oauth",
                    raw={"interface": "oauth", "limit": 1},
                ),
            },
            "redis",
            [
                ("cache", cache_relation),
                ("second_cache", second_cache_relation),
            ],
            id="2 relation",
        ),
    ],
)
def test_get_relations_by_interface(requires, interface_name, expected_relation_list):
    """Test the get_endpoints_by_interface_name function."""
    result = get_endpoints_by_interface_name(requires, interface_name)
    assert result == expected_relation_list


@pytest.mark.parametrize(
    "app_name, unit_identifier, model_name, expected",
    [
        pytest.param(
            "flask-app",
            "0",
            "my-model",
            "flask-app-0.flask-app-endpoints.my-model.svc.cluster.local",
            id="unit number only",
        ),
        pytest.param(
            "flask-app",
            "flask-app/0",
            "production",
            "flask-app-0.flask-app-endpoints.production.svc.cluster.local",
            id="unit name with slash",
        ),
        pytest.param(
            "app",
            "app-1",
            "test",
            "app-1.app-endpoints.test.svc.cluster.local",
            id="unit name with dash",
        ),
        pytest.param(
            "my-service",
            "2",
            "dev-model",
            "my-service-2.my-service-endpoints.dev-model.svc.cluster.local",
            id="hyphenated app name",
        ),
        pytest.param(
            "app",
            "app/10",
            "model",
            "app-10.app-endpoints.model.svc.cluster.local",
            id="double digit unit number",
        ),
    ],
)
def test_build_k8s_unit_fqdn(app_name, unit_identifier, model_name, expected):
    """Test build_k8s_unit_fqdn generates correct Kubernetes FQDN."""
    result = build_k8s_unit_fqdn(app_name, unit_identifier, model_name)
    assert result == expected


def test_validate_cos_custom_dir_accepts_empty_dir(tmp_path: pathlib.Path) -> None:
    """
    arrange: Create an empty directory.
    act: Call validate_cos_custom_dir.
    assert: It should not raise.
    """

    custom_dir = tmp_path / "cos_custom"
    custom_dir.mkdir()

    validate_cos_custom_dir(custom_dir)


def test_validate_cos_custom_dir_rejects_file_in_root(tmp_path: pathlib.Path) -> None:
    """
    arrange: Create a custom COS directory with a file in its root.
    act: Call validate_cos_custom_dir.
    assert: It should raise InvalidCustomCOSDirectoryError.
    """

    custom_dir = tmp_path / "cos_custom"
    custom_dir.mkdir()
    forbidden = custom_dir / "forbidden.txt"
    forbidden.write_text("nope")

    with pytest.raises(InvalidCustomCOSDirectoryError) as exc:
        validate_cos_custom_dir(custom_dir)

    assert "cannot contain a file" in str(exc.value).lower()
    assert forbidden.name in str(exc.value)


def test_validate_cos_custom_dir_rejects_unknown_subdir(tmp_path: pathlib.Path) -> None:
    """
    arrange: Create a custom COS directory with an unexpected subdirectory.
    act: Call validate_cos_custom_dir.
    assert: It should raise InvalidCustomCOSDirectoryError.
    """

    custom_dir = tmp_path / "cos_custom"
    custom_dir.mkdir()
    unknown = custom_dir / "unknown"
    unknown.mkdir()

    with pytest.raises(InvalidCustomCOSDirectoryError) as exc:
        validate_cos_custom_dir(custom_dir)

    assert "cannot contain a subdirectory" in str(exc.value).lower()
    assert unknown.name in str(exc.value)


def test_merge_cos_directories_merges_default_and_custom(tmp_path: pathlib.Path) -> None:
    """
    arrange: Create default and custom COS directory trees with files.
    act: Call merge_cos_directories.
    assert: Default and custom files are merged correctly.
    """

    default_dir = tmp_path / "default"
    (default_dir / "grafana_dashboards").mkdir(parents=True)
    (default_dir / "loki_alert_rules").mkdir(parents=True)
    (default_dir / "prometheus_alert_rules").mkdir(parents=True)
    (default_dir / "grafana_dashboards" / "default.json").write_text("default")

    custom_dir = tmp_path / "custom"
    (custom_dir / "grafana_dashboards").mkdir(parents=True)
    (custom_dir / "grafana_dashboards" / "extra.json").write_text("custom")

    merged_dir = tmp_path / "merged"

    merge_cos_directories(default_dir=default_dir, custom_dir=custom_dir, merged_dir=merged_dir)

    assert (merged_dir / "grafana_dashboards" / "default.json").read_text() == "default"
    assert (merged_dir / "grafana_dashboards" / "custom_extra.json").read_text() == "custom"


def test_merge_cos_directories_uses_default_only_when_custom_missing(
    tmp_path: pathlib.Path,
) -> None:
    """
    arrange: Create default COS tree and point custom COS to a missing path.
    act: Call merge_cos_directories.
    assert: Merged directory contains only default files.
    """

    default_dir = tmp_path / "default"
    (default_dir / "grafana_dashboards").mkdir(parents=True)
    (default_dir / "loki_alert_rules").mkdir(parents=True)
    (default_dir / "prometheus_alert_rules").mkdir(parents=True)
    (default_dir / "grafana_dashboards" / "default.json").write_text("default")

    custom_dir = tmp_path / "custom_missing"
    merged_dir = tmp_path / "merged"

    merge_cos_directories(default_dir=default_dir, custom_dir=custom_dir, merged_dir=merged_dir)

    assert (merged_dir / "grafana_dashboards" / "default.json").read_text() == "default"
    assert list((merged_dir / "grafana_dashboards").glob("custom_*")) == []


def test_merge_cos_directories_uses_default_only_when_custom_invalid(
    tmp_path: pathlib.Path,
) -> None:
    """
    arrange: Create default COS tree and invalid custom COS tree.
    act: Call merge_cos_directories.
    assert: Merged directory contains only default files.
    """

    default_dir = tmp_path / "default"
    (default_dir / "grafana_dashboards").mkdir(parents=True)
    (default_dir / "loki_alert_rules").mkdir(parents=True)
    (default_dir / "prometheus_alert_rules").mkdir(parents=True)
    (default_dir / "grafana_dashboards" / "default.json").write_text("default")

    custom_dir = tmp_path / "custom_invalid"
    custom_dir.mkdir()
    (custom_dir / "grafana_dashboards").mkdir(parents=True)
    (custom_dir / "grafana_dashboards" / "extra.json").write_text("custom")
    (custom_dir / "invalid.txt").write_text("invalid")

    merged_dir = tmp_path / "merged"

    merge_cos_directories(default_dir=default_dir, custom_dir=custom_dir, merged_dir=merged_dir)

    assert (merged_dir / "grafana_dashboards" / "default.json").read_text() == "default"
    assert not (merged_dir / "grafana_dashboards" / "custom_extra.json").exists()
