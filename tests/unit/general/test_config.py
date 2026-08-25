# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utils unit tests."""

import pathlib
import unittest

import ops
import pytest
import yaml
from ops import testing
from pydantic import Field

import paas_charm
from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from paas_charm.charm_state import _create_config_attribute
from paas_charm.exceptions import CharmConfigInvalidError
from paas_charm.utils import config_metadata


@pytest.mark.parametrize(
    "charm_type",
    [
        FlaskCharm,
        GoCharm,
        FastAPICharm,
        DjangoCharm,
        ExpressJSCharm,
    ],
)
@pytest.mark.parametrize(
    "required_configs, expected_status_message_substrs, unexpected_status_message_substrs, expected_log_message_substrs",
    [
        pytest.param(
            [
                {
                    "non-optional-bool": {
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
                    "non-optional-int": {
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
                    "non-optional-float": {
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
                    "non-optional-string": {
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
                    "non-optional-secret": {
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
                    "non-optional-bool": {
                        "description": "A non-optional config option for testing.",
                        "type": "boolean",
                        "optional": False,
                    }
                },
                {
                    "non-optional-int": {
                        "description": "A non-optional config option for testing.",
                        "type": "int",
                        "optional": False,
                    }
                },
                {
                    "non-optional-float": {
                        "description": "A non-optional config option for testing.",
                        "type": "float",
                        "optional": False,
                    }
                },
                {
                    "non-optional-string": {
                        "description": "A non-optional config option for testing.",
                        "type": "string",
                        "optional": False,
                    }
                },
                {
                    "non-optional-secret": {
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
    charm_type: type,
    context_factory,
    framework_state_factory,
    required_configs: list[dict],
    expected_status_message_substrs: list[str],
    unexpected_status_message_substrs: list[str],
    expected_log_message_substrs: list[str],
    charm_root,
    monkeypatch,
    caplog,
) -> None:
    """
    arrange: Deploy charm with fake config options in charmcraft.yaml.
    act: Try to create charm state.
    assert: The charm should be in blocked state with correct message and logs.
    """
    charm_dir = charm_root(charm_type)
    config_file = charm_dir / "charmcraft.yaml"
    yaml_dict = yaml.safe_load(config_file.read_text())
    for config in required_configs:
        yaml_dict["config"]["options"].update(config)
    monkeypatch.setattr(
        paas_charm.charm_state,
        "config_metadata",
        unittest.mock.MagicMock(return_value=yaml_dict["config"]),
    )
    context = context_factory(charm_type)
    state_dict = framework_state_factory(charm_type)
    if any("non-optional-string" in config for config in required_configs):
        state_dict["config"].pop("non-optional-string", None)
    state = testing.State(**state_dict)
    with context(context.on.config_changed(), state) as manager:
        with pytest.raises(CharmConfigInvalidError) as exc:
            manager.charm._create_charm_state()
    assert "missing options" in str(exc.value).lower()
    out = context.run(context.on.config_changed(), state)
    assert isinstance(out.unit_status, ops.model.BlockedStatus)
    for substr in expected_log_message_substrs:
        assert substr in caplog.text.lower()
    for substr in expected_status_message_substrs:
        assert substr in out.unit_status.message.lower()
    for substr in unexpected_status_message_substrs:
        assert substr not in out.unit_status.message.lower()


@pytest.mark.parametrize(
    "charm_type, prefix",
    [
        [FlaskCharm, "flask"],
        [GoCharm, "app"],
        [ExpressJSCharm, "app"],
        [FastAPICharm, "app"],
        [DjangoCharm, "django"],
    ],
)
def test_get_framework_config_with_prefix(
    charm_type: type,
    prefix: str,
    charm_root,
    context_factory,
    framework_state_factory,
) -> None:
    """
    arrange: Get the config options with framework related prefix.
    act: Start the charm and get the framework config object
    assert: Framework config object should have the framework related prefixed config options as attributes.
    """
    charm_dir = charm_root(charm_type)
    metadata = config_metadata(charm_dir)
    framework_keys = [
        option[6:].replace("-", "_") for option in metadata["options"] if option.startswith(prefix)
    ]

    context = context_factory(charm_type)
    with context(
        context.on.config_changed(),
        testing.State(**framework_state_factory(charm_type)),
    ) as manager:
        framework_config = manager.charm.get_framework_config()

    assert list(framework_config.__annotations__.keys()).sort() == framework_keys.sort()


@pytest.mark.parametrize(
    "charm_type, secret_key, expected_status_message_substrs, unexpected_status_message_substrs, expected_log_message_substrs",
    [
        pytest.param(
            FlaskCharm,
            "app-secret-key",
            ["invalid", "app-secret-key"],
            ["valid string"],
            ["invalid", "config", "app-secret-key", "at least 1 character"],
        ),
        pytest.param(
            ExpressJSCharm,
            "app-secret-key",
            ["invalid", "app-secret-key"],
            ["valid string"],
            ["invalid", "config", "app-secret-key", "at least 1 character"],
        ),
        pytest.param(
            GoCharm,
            "app-secret-key",
            ["invalid", "app-secret-key"],
            ["valid string"],
            ["invalid", "config", "app-secret-key", "at least 1 character"],
        ),
        pytest.param(
            FastAPICharm,
            "app-secret-key",
            ["invalid", "app-secret-key"],
            ["valid string"],
            ["invalid", "config", "app-secret-key", "at least 1 character"],
        ),
        pytest.param(
            DjangoCharm,
            "app-secret-key",
            ["invalid", "app-secret-key"],
            ["valid string"],
            ["invalid", "config", "app-secret-key", "at least 1 character"],
        ),
    ],
)
def test_get_framework_config_invalid(
    charm_type: type,
    secret_key: str,
    expected_status_message_substrs: list[str],
    unexpected_status_message_substrs: list[str],
    expected_log_message_substrs: list[str],
    context_factory,
    framework_state_factory,
    caplog,
) -> None:
    """
    arrange: Get the charm.
    act: Set a config option to empty string.
    assert: Charm should raise a CharmConfigInvalidError.
    """
    context = context_factory(charm_type)
    state_dict = framework_state_factory(charm_type)
    with context(context.on.config_changed(), testing.State(**state_dict)) as manager:
        manager.charm.config._lazy_data = {
            **manager.charm.config,
            secret_key: "",
        }
        with pytest.raises(CharmConfigInvalidError) as exc:
            manager.charm.get_framework_config()
        manager.charm._reconcile()
        status = manager.charm.unit.status
    assert "invalid options" in str(exc.value).lower()
    assert isinstance(status, ops.model.BlockedStatus)
    for substr in expected_log_message_substrs:
        assert substr in caplog.text.lower()
    for substr in expected_status_message_substrs:
        assert substr in status.message.lower()
    for substr in unexpected_status_message_substrs:
        assert substr not in status.message.lower()


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
        pytest.param(
            option["name"],
            option["type_dict"],
            option["type_result"],
            id=option["name"],
        )
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
            "webserver-option": {"type": "string"},
            "app-option": {"type": "string"},
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
@pytest.mark.parametrize("framework", ["flask", "go", "fastapi", "django", "expressjs"])
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

    mock_charm = unittest.mock.MagicMock()
    mock_charm.charm_dir = pathlib.Path(".")

    assert (
        paas_charm.charm_state.app_config_class_factory(mock_charm, framework).__annotations__
        == expected_output
    )


@pytest.mark.parametrize(
    "charm_type, framework, app_prefix",
    [
        pytest.param(FlaskCharm, "flask", "FLASK", id="flask"),
        pytest.param(DjangoCharm, "django", "DJANGO", id="django"),
        pytest.param(
            FastAPICharm,
            "fastapi",
            "APP",
            id="fastapi",
        ),
        pytest.param(GoCharm, "go", "APP", id="go"),
    ],
)
def test_secret_storage_config(
    charm_type: type,
    framework: str,
    app_prefix: str,
    context_factory,
    framework_state_factory,
):
    """
    arrange: Run initial hooks.
    act: Add two units to the secret-storage relation.
    assert: The app service must have the right peer configuration.
    """
    state_dict = framework_state_factory(charm_type)
    peer_relation = next(
        relation for relation in state_dict["relations"] if relation.endpoint == "secret-storage"
    )
    state_dict["relations"].remove(peer_relation)
    peer_relation = testing.PeerRelation(
        "secret-storage",
        local_app_data=peer_relation.local_app_data,
        peers_data={1: {}, 2: {}},
    )
    state_dict["relations"].append(peer_relation)
    context = context_factory(charm_type)
    with context(context.on.config_changed(), testing.State(**state_dict)) as manager:
        manager.charm._secret_storage.get_secret_key = unittest.mock.MagicMock(
            return_value="foobar"
        )
        out = manager.run()
    service_env = out.get_container("app").plan.services[framework].environment
    expected_output = f"{framework}-k8s-1.{framework}-k8s-endpoints.test-model.svc.cluster.local,{framework}-k8s-2.{framework}-k8s-endpoints.test-model.svc.cluster.local"
    assert service_env[f"{app_prefix}_PEER_FQDNS"] == expected_output
