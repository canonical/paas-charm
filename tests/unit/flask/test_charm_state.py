# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Flask charm state unit tests."""

import os
import pathlib
from secrets import token_hex

import pytest
import yaml
from ops import testing

from examples.flask.charm.src.charm import FlaskCharm

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent


@pytest.fixture(scope="function", name="flask_base_state")
def flask_base_state_fixture():
    """State with container and config file set."""
    os.chdir(PROJECT_ROOT / "examples/flask/charm")
    yield {
        "relations": [
            testing.PeerRelation(
                "secret-storage", local_app_data={"flask_secret_key": "test", "secret": "test"}
            ),
        ],
        "containers": {
            testing.Container(
                name="app",
                can_connect=True,
                mounts={"data": testing.Mount(location="/flask/gunicorn.conf.py", source="conf")},
                execs={
                    testing.Exec(
                        command_prefix=["/bin/python3"],
                        return_code=0,
                    ),
                },
                _base_plan={
                    "services": {
                        "flask": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/bin/python3 -m gunicorn -c /flask/gunicorn.conf.py app:app -k [ sync ]",
                        }
                    }
                },
            )
        },
        "model": testing.Model(name="test-model"),
    }


CHARM_STATE_FLASK_CONFIG_TEST_PARAMS = [
    pytest.param(
        {"flask-env": "prod"},
        {"FLASK_ENV": "prod", "FLASK_PREFERRED_URL_SCHEME": "HTTPS"},
        id="env",
    ),
    pytest.param(
        {"flask-debug": True},
        {"FLASK_DEBUG": "true", "FLASK_PREFERRED_URL_SCHEME": "HTTPS"},
        id="debug",
    ),
    pytest.param(
        {"app-secret-key": "1234"},
        {"FLASK_SECRET_KEY": "1234", "FLASK_PREFERRED_URL_SCHEME": "HTTPS"},
        id="secret-key",
    ),
    pytest.param(
        {"flask-preferred-url-scheme": "http"},
        {"FLASK_PREFERRED_URL_SCHEME": "HTTP"},
        id="preferred-url-scheme",
    ),
]


@pytest.mark.parametrize("charm_config, expected_env", CHARM_STATE_FLASK_CONFIG_TEST_PARAMS)
def test_charm_state_flask_config(
    flask_base_state, charm_config: dict, expected_env: dict
) -> None:
    """
    arrange: none
    act: set flask_* charm configurations.
    assert: flask_config in the charm state should reflect changes in charm configurations.
    """
    flask_base_state["config"] = charm_config

    ctx = testing.Context(FlaskCharm)
    state = testing.State(**flask_base_state)

    out = ctx.run(ctx.on.config_changed(), state)

    plan = list(out.containers)[0].plan
    service = plan.services["flask"]
    for key, value in expected_env.items():
        assert service.environment.get(key) == value


@pytest.mark.parametrize(
    "charm_config",
    [
        pytest.param({"flask-env": ""}, id="env"),
        pytest.param({"app-secret-key": ""}, id="secret-key"),
        pytest.param(
            {"flask-preferred-url-scheme": "tls"},
            id="preferred-url-scheme",
        ),
    ],
)
def test_charm_state_invalid_flask_config(flask_base_state, charm_config: dict) -> None:
    """
    arrange: none
    act: set flask_* charm configurations to be invalid values.
    assert: the CharmState should raise a CharmConfigInvalidError exception
    """
    flask_base_state["config"] = charm_config
    ctx = testing.Context(FlaskCharm)
    state = testing.State(**flask_base_state)

    out = ctx.run(ctx.on.config_changed(), state)

    # Expect blocked status because invalid config
    assert isinstance(out.unit_status, testing.BlockedStatus)
    assert "invalid option" in out.unit_status.message


@pytest.mark.parametrize(
    "s3_connection_info, expected_s3_env",
    [
        pytest.param(None, {}, id="empty"),
        pytest.param(
            {
                "access-key": "access-key",
                "secret-key": "secret-key",
                "bucket": "bucket",
            },
            {
                "S3_ACCESS_KEY": "access-key",
                "S3_SECRET_KEY": "secret-key",
                "S3_BUCKET": "bucket",
            },
            id="with data",
        ),
    ],
)
def test_s3_integration(flask_base_state, s3_connection_info, expected_s3_env):
    """
    arrange: Prepare charm and charm config.
    act: Create the CharmState with s3 information.
    assert: Check the S3Parameters generated are the expected ones.
    """
    if s3_connection_info:
        s3_relation = testing.Relation(
            endpoint="s3",
            interface="s3",
            remote_app_data=s3_connection_info,
        )
        flask_base_state["relations"].append(s3_relation)

    ctx = testing.Context(FlaskCharm)
    state = testing.State(**flask_base_state)

    out = ctx.run(ctx.on.config_changed(), state)

    plan = list(out.containers)[0].plan
    service = plan.services["flask"]

    if not expected_s3_env:
        # Check that no S3 env vars exist
        for key in service.environment:
            assert not key.startswith("S3_")
    else:
        for key, value in expected_s3_env.items():
            assert service.environment.get(key) == value


@pytest.mark.parametrize(
    "s3_uri_style, addressing_style",
    [("host", "virtual"), ("path", "path"), (None, None)],
)
def test_s3_addressing_style(flask_base_state, s3_uri_style, addressing_style) -> None:
    """
    arrange: Create s3 relation data with different s3_uri_styles.
    act: Create S3Parameters pydantic BaseModel from relation data.
    assert: Check that s3_uri_style is a valid addressing style.
    """
    s3_relation_data = {
        "access-key": token_hex(16),
        "secret-key": token_hex(16),
        "bucket": "backup-bucket",
        "region": "us-west-2",
    }
    if s3_uri_style:
        s3_relation_data["s3-uri-style"] = s3_uri_style

    flask_base_state["relations"].append(
        testing.Relation(
            endpoint="s3",
            interface="s3",
            remote_app_data=s3_relation_data,
        )
    )

    ctx = testing.Context(FlaskCharm)
    state = testing.State(**flask_base_state)
    out = ctx.run(ctx.on.config_changed(), state)

    plan = list(out.containers)[0].plan
    env = plan.services["flask"].environment

    assert env.get("S3_ADDRESSING_STYLE") == addressing_style


def test_secret_configuration(flask_base_state):
    """
    arrange: prepare a juju secret configuration.
    act: set secret-test charm configurations.
    assert: user_defined_config in the charm state should contain the value of the secret \
        configuration.
    """
    secret = testing.Secret(
        tracked_content={"foo": "foo", "bar": "bar", "foo-bar": "foobar"},
    )
    flask_base_state["secrets"] = [secret]
    flask_base_state["config"] = {"secret-test": secret.id}

    ctx = testing.Context(FlaskCharm)
    state = testing.State(**flask_base_state)
    out = ctx.run(ctx.on.config_changed(), state)

    plan = list(out.containers)[0].plan
    env = plan.services["flask"].environment

    # secret-test -> SECRET_TEST
    # foo -> FOO
    # Expect: FLASK_SECRET_TEST_FOO=foo
    assert env.get("FLASK_SECRET_TEST_FOO") == "foo"
    assert env.get("FLASK_SECRET_TEST_BAR") == "bar"
    assert env.get("FLASK_SECRET_TEST_FOO_BAR") == "foobar"


def test_flask_secret_key_id_no_value(flask_base_state):
    """
    arrange: Prepare an invalid app-secret-key-id secret.
    act: Try to build CharmState.
    assert: It should raise CharmConfigInvalidError.
    """
    # The secret should contain "value", but here we give "wrong-key"
    key_secret = testing.Secret(owner="app", tracked_content={"wrong-key": "foobar"})
    flask_base_state["secrets"] = [key_secret]

    flask_base_state["config"] = {"app-secret-key-id": key_secret.id}

    ctx = testing.Context(FlaskCharm)
    state = testing.State(**flask_base_state)
    out = ctx.run(ctx.on.config_changed(), state)

    assert isinstance(out.unit_status, testing.BlockedStatus)
    assert "invalid option" in out.unit_status.message


def test_flask_secret_key_id_duplication(flask_base_state):
    """
    arrange: Provide both the app-secret-key-id and app-secret-key configuration.
    act: Try to build CharmState.
    assert: It should raise CharmConfigInvalidError.
    """
    secret = testing.Secret(tracked_content={"value": "foobar"})
    flask_base_state["secrets"] = [secret]
    flask_base_state["config"] = {
        "app-secret-key-id": secret.id,
        "app-secret-key": "test",
    }

    ctx = testing.Context(FlaskCharm)
    state = testing.State(**flask_base_state)
    out = ctx.run(ctx.on.config_changed(), state)

    assert isinstance(out.unit_status, testing.BlockedStatus)
    assert "invalid option" in out.unit_status.message


@pytest.mark.parametrize("charm_config, expected_env", CHARM_STATE_FLASK_CONFIG_TEST_PARAMS)
def test_charm_state_paas_config(
    flask_base_state, modify_paas_config, charm_config: dict, expected_env: dict
) -> None:
    """
    arrange: none
    act: set flask_* charm configurations.
    assert: flask_config in the charm state should reflect changes in charm configurations.
    """
    flask_base_state["config"] = charm_config

    modify_paas_config(8081, 8082, "/alternative_metrics")

    ctx = testing.Context(FlaskCharm)
    state = testing.State(**flask_base_state)

    out = ctx.run(ctx.on.config_changed(), state)

    plan = list(out.containers)[0].plan
    service = plan.services["flask"]
    for key, value in expected_env.items():
        assert service.environment.get(key) == value


@pytest.fixture(name="modify_paas_config")
def modify_paas_config_fixture():
    """Temporarily modify paas-config.yaml and revert to the original after the test."""
    paas_config_path = PROJECT_ROOT / "examples/flask/charm/paas-config.yaml"
    original_content = paas_config_path.read_text()

    def _modify(port: int, metrics_port: int, metrics_path: str) -> None:
        config = yaml.safe_load(original_content)
        config["port"] = port
        config["metrics-port"] = metrics_port
        config["metrics-path"] = metrics_path
        paas_config_path.write_text(yaml.dump(config))

    yield _modify

    paas_config_path.write_text(original_content)
