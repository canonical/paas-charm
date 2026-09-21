# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exercise real integration fixtures under pytest without a cluster or builds."""

import os
import pathlib
import textwrap
from unittest.mock import Mock

import pytest

from tests.integration import conftest as fixtures

pytest_plugins = ["pytester"]

ROOT = pathlib.Path(__file__).resolve().parents[2]

HARNESS = """
import concurrent.futures
import pathlib
import threading
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from tests.integration.conftest import *
from tests.conftest import pytest_addoption

EXPECTED = {expected!r}
PREEXISTING = {preexisting!r}
FAIL = {fail!r}
STOP = {stop!r}
EVENTS = []
RELEASED = threading.Event()
REQUESTED = threading.Event()


class AppDeployed(Exception):
    pass


@pytest.fixture(scope="session")
def gate():
    def inspect_pending_build():
        assert REQUESTED.wait(10), "artifacts were never requested"
        try:
            deployed = {{event[1] for event in EVENTS if event[0] == "external"}}
            assert deployed == set(EXPECTED), EVENTS
            assert not any(event[0] == "app" for event in EVENTS), EVENTS
        finally:
            EVENTS.append(("release",))
            RELEASED.set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(inspect_pending_build)
        yield
        pending.result(timeout=10)


@pytest.fixture(scope="session")
def juju(gate):
    apps = {{}}
    status = SimpleNamespace(
        apps=apps, model=SimpleNamespace(name="test-model", controller="test-controller")
    )
    def add_app(name):
        unit = SimpleNamespace(address="10.0.0.7", leader=True)
        apps[name] = SimpleNamespace(
            units={{f"{{name}}/0": unit}}, is_active=True, is_blocked=True, relations={{}}
        )
    for name in PREEXISTING:
        add_app(name)
    client = Mock()
    client.status.return_value = status
    def deploy(charm, app=None, **kwargs):
        if str(charm).endswith(".charm"):
            assert RELEASED.is_set(), "app deployed before artifact readiness"
            assert kwargs["resources"]["app-image"].startswith("registry.test/")
            name = app or pathlib.Path(charm).stem
            EVENTS.append(("app", name, kwargs["resources"]["app-image"]))
            add_app(name)
            if STOP:
                raise AppDeployed(name)
        else:
            assert not REQUESTED.is_set(), "external deployed after artifact gate"
            name = app or charm
            EVENTS.append(("external", name, kwargs))
            add_app(name)
    client.deploy.side_effect = deploy
    client.wait.side_effect = lambda *args, **kwargs: EVENTS.append(("wait",))
    client.config.side_effect = lambda *args, **kwargs: EVENTS.append(("config", args))
    return client


@pytest.fixture(scope="session", name="charm_paths")
def fixture_charm_paths(tmp_path_factory, gate):
    EVENTS.append(("artifact-wait",))
    REQUESTED.set()
    assert RELEASED.wait(10), "build gate did not release"
    if FAIL:
        raise RuntimeError("artifact build failed")
    paths = {{}}
    directory = tmp_path_factory.mktemp("artifacts")
    for framework in ("flask", "django", "fastapi", "go", "expressjs",
                      "spring-boot", "flask-minimal"):
        key = f"{{framework}}-k8s"
        path = directory / f"{{key}}.charm"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("config.yaml", "options: {{}}")
            archive.writestr("metadata.yaml", f"name: {{key}}")
            archive.writestr("actions.yaml", "{{}}")
        paths[key] = path
    return paths


@pytest.fixture(scope="session", name="rock_images")
def fixture_rock_images(charm_paths):
    EVENTS.append(("images",))
    return {{name: f"registry.test/{{name}}:built" for name in (
        "test-flask", "test-db-flask", "test-async-flask", "django-app",
        "django-async-app", "fastapi-app", "go-app", "expressjs-app",
        "paas-spring-boot-app", "flask-minimal-app"
    )}}
"""


def make_suite(
    pytester, monkeypatch, expected=(), *, preexisting=(), fail=False, stop=False, extra=""
):
    """Install the real fixtures with only infrastructure/artifacts mocked."""
    monkeypatch.setenv(
        "PYTHONPATH", os.pathsep.join((str(ROOT), os.environ.get("PYTHONPATH", "")))
    )
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    pytester.makeini(
        "[pytest]\nmarkers = early_dependencies(*fixtures): selected external deployments\n"
    )
    pytester.makeconftest(
        HARNESS.format(expected=expected, preexisting=preexisting, fail=fail, stop=stop)
        + textwrap.dedent(extra)
    )


APPS = [
    ("flask_app", False),
    ("flask_db_app", True),
    ("flask_async_app", False),
    ("flask_non_root_app", False),
    ("flask_non_root_db_app", True),
    ("django_app", True),
    ("django_async_app", True),
    ("django_non_root_app", True),
    ("fastapi_app", True),
    ("fastapi_non_root_app", True),
    ("go_app", True),
    ("go_non_root_app", True),
    ("expressjs_app", True),
    ("expressjs_non_root_app", True),
    ("spring_boot_app", True),
    ("spring_boot_mysql_app", False),
    ("flask_blocked_app", False),
    ("django_blocked_app", True),
    ("fastapi_blocked_app", True),
    ("go_blocked_app", True),
    ("expressjs_blocked_app", True),
]


@pytest.mark.parametrize("app_fixture,postgres", APPS)
@pytest.mark.parametrize("dynamic", [False, True], ids=["static", "dynamic"])
def test_framework_fixture_gate(pytester, monkeypatch, app_fixture, postgres, dynamic):
    """Every app variant orders its required DB before session artifact fixtures."""
    make_suite(pytester, monkeypatch, ("postgresql-k8s",) if postgres else ())
    signature = "request" if dynamic else app_fixture
    expression = f'request.getfixturevalue("{app_fixture}")' if dynamic else app_fixture
    pytester.makepyfile(f"""
        from conftest import EVENTS
        def test_app({signature}):
            assert {expression}.name.endswith("-k8s")
            kinds = [event[0] for event in EVENTS]
            assert kinds.index("artifact-wait") < kinds.index("release")
            assert kinds.index("release") < kinds.index("images") < kinds.index("app")
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "app_fixture", ["flask_minimal_app", "fastapi_app", "go_app", "expressjs_app"]
)
def test_integration_overrides(pytester, monkeypatch, app_fixture):
    """Integration-directory overrides use the same gate, including the minimal app."""
    make_suite(
        pytester,
        monkeypatch,
        () if app_fixture == "flask_minimal_app" else ("postgresql-k8s",),
        extra=f"from tests.integration.integrations.conftest import {app_fixture}_fixture",
    )
    pytester.makepyfile(f"def test_app({app_fixture}): assert {app_fixture}.name")
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


def test_session_artifacts_and_database_reused(pytester, monkeypatch):
    """Multiple apps share one artifact preparation and reuse the existing database."""
    make_suite(pytester, monkeypatch, preexisting=("postgresql-k8s",))
    pytester.makepyfile("""
        from conftest import EVENTS
        def test_first(django_app): pass
        def test_second(go_app):
            assert sum(event[0] == "artifact-wait" for event in EVENTS) == 1
            assert sum(event[0] == "app" for event in EVENTS) == 2
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=2)


def test_selected_tracing_reuses_existing_tempo(pytester, monkeypatch):
    """Early module setup retains the tracing test's existing-model reuse."""
    make_suite(
        pytester,
        monkeypatch,
        preexisting=("tempo",),
        extra="from tests.integration.integrations.conftest import tempo_app_fixture",
    )
    pytester.makepyfile("""
        import pytest
        pytestmark = pytest.mark.early_dependencies("tempo_app")
        def test_reuse(flask_app, tempo_app):
            assert tempo_app.name == "tempo"
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


def test_artifact_failure_does_not_deploy_app(pytester, monkeypatch):
    """Failed artifact preparation propagates after external deployment."""
    make_suite(pytester, monkeypatch, ("postgresql-k8s",), fail=True)
    pytester.makepyfile("""
        import pytest
        from conftest import EVENTS
        def test_failure(request):
            with pytest.raises(RuntimeError, match="artifact build failed"):
                request.getfixturevalue("go_app")
            assert not any(event[0] == "app" for event in EVENTS)
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


CASES = [
    ("flask.test_charm", "test_with_ingress", {}, ("gateway", "configurator", "cert")),
    ("go.test_go", "test_open_ports", {}, ("gateway", "configurator", "cert", "postgresql-k8s")),
    (
        "flask.test_database",
        "test_with_database",
        {
            "endpoint": "postgresql/status",
            "db_name": "postgresql-k8s",
            "db_channel": "14/edge",
            "revision": None,
            "trust": True,
        },
        ("postgresql-k8s",),
    ),
    (
        "integrations.test_prometheus",
        "test_prometheus_custom_scrape_configs",
        {},
        ("prometheus-k8s",),
    ),
    (
        "integrations.test_rabbitmq",
        "test_rabbitmq_server_integration",
        {"app_fixture": "go_app", "port": 8080, "rabbitmq_app_fixture": "rabbitmq_k8s_app"},
        ("rabbitmq-k8s", "postgresql-k8s"),
    ),
    (
        "integrations.test_rabbitmq",
        "test_rabbitmq_server_integration",
        {"app_fixture": "go_app", "port": 8080, "rabbitmq_app_fixture": "rabbitmq_server_app"},
        ("rabbitmq-server", "postgresql-k8s"),
    ),
    (
        "integrations.test_rabbitmq",
        "test_rabbitmq_ha_integration",
        {},
        ("rabbitmq-server", "postgresql-k8s"),
    ),
    (
        "integrations.test_smtp",
        "test_smtp_integrations",
        {"app_fixture": "django_app", "port": 8000},
        ("smtp-integrator", "postgresql-k8s"),
    ),
    (
        "integrations.test_saml",
        "test_saml_integration",
        {"app_fixture": "flask_app", "port": 8000},
        ("saml-integrator",),
    ),
    ("flask.test_proxy", "test_proxy", {}, ()),
]


@pytest.mark.parametrize("module,function,parameters,expected", CASES)
def test_selected_test_dependencies(pytester, monkeypatch, module, function, parameters, expected):
    """Run actual test setup until app deployment, checking every external precedes the gate."""
    extra = """
        from tests.integration.integrations.conftest import (
            deploy_prometheus_fixture, deploy_rabbitmq_k8s_fixture,
            prometheus_app_name_fixture,
            deploy_rabbitmq_server_fixture, deploy_rabbitmq_server_ha_fixture,
            lxd_controller, lxd_controller_name_fixture, lxd_model_fixture,
            lxd_model_name_fixture, s3_configuration_fixture, s3_credentials_fixture,
            minio_app_name_fixture,
        )
        @pytest.fixture(scope="module")
        def mailcatcher():
            return SimpleNamespace(host="mail.test", port=1025, pod_ip="10.0.0.8")
    """
    make_suite(pytester, monkeypatch, expected, stop=True, extra=extra)
    pytester.makepyfile(f"""
        import inspect
        import pytest
        from unittest.mock import Mock
        from conftest import AppDeployed, EVENTS
        from tests.integration.{module} import {function} as selected

        def test_selected(request, monkeypatch):
            if {module!r} == "integrations.test_saml":
                monkeypatch.setattr(
                    "saml_test_helper.SamlK8sTestHelper.deploy_saml_idp", Mock()
                )
            values = {parameters!r}
            with pytest.raises(AppDeployed):
                for name in inspect.signature(selected).parameters:
                    if name not in values:
                        values[name] = request if name == "request" else request.getfixturevalue(name)
                selected(**values)
            assert sum(event[0] == "app" for event in EVENTS) == 1
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


def test_workers_only_deploy_valkey_when_selected(pytester, monkeypatch):
    """The worker relation fixture starts Valkey; the async worker does not."""
    make_suite(
        pytester,
        monkeypatch,
        ("valkey",),
        stop=True,
        extra="from tests.integration.flask.test_workers import valkey_app_fixture, integrate_valkey_flask_fixture",
    )
    pytester.makepyfile("""
        import pytest
        from conftest import AppDeployed
        def test_workers(request):
            with pytest.raises(AppDeployed):
                request.getfixturevalue("integrate_valkey_flask")
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


@pytest.mark.parametrize("only_first", [False, True], ids=["whole-module", "deselected"])
def test_later_selected_dependency_precedes_first_gate(pytester, monkeypatch, only_first):
    """A later test's dependency starts before the first app, but not when deselected."""
    make_suite(
        pytester,
        monkeypatch,
        () if only_first else ("gateway", "configurator", "cert"),
    )
    pytester.makepyfile("""
        import pytest
        def test_first(flask_app):
            assert flask_app.name == "flask-k8s"
        @pytest.mark.early_dependencies("ingress_provider")
        def test_later(flask_app, ingress_provider):
            assert ingress_provider == ("gateway", "configurator")
        """)
    arguments = ("-k", "test_first") if only_first else ()
    pytester.runpytest_subprocess("-q", *arguments).assert_outcomes(
        passed=1 if only_first else 2, deselected=1 if only_first else 0
    )


@pytest.mark.parametrize("only_flask", [False, True], ids=["whole-module", "flask-only"])
def test_later_database_parameter_selected(pytester, monkeypatch, only_flask):
    """A selected DB-backed parameter starts PostgreSQL even if Flask runs first."""
    make_suite(pytester, monkeypatch, () if only_flask else ("postgresql-k8s",))
    pytester.makepyfile("""
        import pytest
        @pytest.mark.parametrize("app_fixture", [
            "flask_app",
            pytest.param("django_app", marks=pytest.mark.early_dependencies("postgresql_app")),
        ])
        def test_app(request, app_fixture):
            assert request.getfixturevalue(app_fixture).name
        """)
    arguments = ("-k", "flask") if only_flask else ()
    pytester.runpytest_subprocess("-q", *arguments).assert_outcomes(
        passed=1 if only_flask else 2, deselected=1 if only_flask else 0
    )


def test_spring_saml_address_dependent_configuration(pytester, monkeypatch):
    """SAML deploys before artifacts, but IDP addresses/config use the real app IP."""
    make_suite(
        pytester,
        monkeypatch,
        ("saml-integrator", "postgresql-k8s"),
        extra="""
            from tests.integration.springboot.conftest import (
                spring_boot_unit_ip_fixture, simplesamlphp_ip_fixture,
                saml_integrator_app_fixture, saml_integrator_fixture,
            )
        """,
    )
    pytester.makepyfile("""
        from types import SimpleNamespace
        from unittest.mock import Mock
        from conftest import EVENTS

        def test_saml(request, monkeypatch):
            api = Mock()
            api.read_namespaced_pod.return_value = SimpleNamespace(
                status=SimpleNamespace(phase="Running", pod_ip="10.0.0.8")
            )
            monkeypatch.setattr("kubernetes.client.CoreV1Api", lambda: api)
            monkeypatch.setattr("kubernetes.config.load_kube_config", Mock())
            assert request.getfixturevalue("saml_integrator").name == "saml-integrator"
            pod = api.create_namespaced_pod.call_args.kwargs["body"]
            environment = {v.name: v.value for v in pod.spec.containers[0].env}
            assert environment["SIMPLESAMLPHP_SP_ENTITY_ID"] == "10.0.0.7:8080"
            assert environment["SIMPLESAMLPHP_SP_ASSERTION_CONSUMER_SERVICE"] == (
                "http://10.0.0.7:8080/login/saml2/sso/testentity"
            )
            kinds = [event[0] for event in EVENTS]
            assert kinds.index("app") < kinds.index("config")
            config = next(event[1][1] for event in EVENTS if event[0] == "config")
            assert config["metadata_url"] == (
                "http://10.0.0.8:8080/simplesaml/saml2/idp/metadata.php"
            )
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


def test_missing_image_never_deploys_app(pytester, monkeypatch):
    """A missing image is an error, not an empty deployment resource."""
    make_suite(
        pytester,
        monkeypatch,
        ("postgresql-k8s",),
        extra="""
            @pytest.fixture(scope="session", name="rock_images")
            def fixture_rock_images(charm_paths):
                return {}
        """,
    )
    pytester.makepyfile("""
        import pytest
        from conftest import EVENTS
        def test_missing(request):
            with pytest.raises(ValueError, match="go-app rock image not found"):
                request.getfixturevalue("go_app")
            assert not any(event[0] == "app" for event in EVENTS)
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


def test_external_failure_does_not_resolve_artifacts(pytester, monkeypatch):
    """External deployment failures cannot fall through to app artifact preparation."""
    make_suite(
        pytester,
        monkeypatch,
        extra="""
            @pytest.fixture(scope="session")
            def gate():
                yield
                assert not REQUESTED.is_set()
        """,
    )
    pytester.makepyfile("""
        import pytest
        def test_failure(request, juju):
            juju.deploy.side_effect = RuntimeError("database deploy failed")
            with pytest.raises(RuntimeError, match="database deploy failed"):
                request.getfixturevalue("go_app")
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


@pytest.mark.parametrize("failed_build", [False, True], ids=["ready", "failed-build"])
def test_opcli_plugin_gate(pytester, monkeypatch, failed_build):
    """Exercise the real plugin gate, manifest adapters and image preparation."""
    make_suite(
        pytester,
        monkeypatch,
        ("postgresql-k8s",),
        extra=f"""
            import platform
            import yaml
            from opcli.core import artifact_preparation
            from tests.integration.conftest import fixture_charm_paths, fixture_rock_images

            pytest_plugins = ["opcli.pytest_plugin"]
            FAILED_BUILD = {failed_build!r}

            @pytest.fixture(scope="session", autouse=True)
            def artifact_backend():
                root = pathlib.Path.cwd()
                (root / "artifacts.yaml").write_text("version: 1")
                architecture = {{"x86_64": "amd64", "aarch64": "arm64"}}[platform.machine()]
                def fetch(directory, run_id, repo, **kwargs):
                    assert directory == root
                    assert (run_id, repo) == ("123", "canonical/paas-charm")
                    assert kwargs == {{"wait": True, "wait_timeout": 17}}
                    EVENTS.append(("artifact-wait",))
                    REQUESTED.set()
                    assert RELEASED.wait(10)
                    if FAILED_BUILD:
                        raise RuntimeError("artifact build failed")
                    build = root / "build"
                    build.mkdir()
                    with zipfile.ZipFile(build / "go-k8s.charm", "w") as archive:
                        archive.writestr("config.yaml", "options: {{}}")
                        archive.writestr("metadata.yaml", "name: go-k8s")
                        archive.writestr("actions.yaml", "{{}}")
                    (build / "go-app.rock").write_bytes(b"rock")
                    manifest = {{
                        "version": 1,
                        "charms": [{{
                            "name": "go-k8s", "charmcraft-yaml": "charmcraft.yaml",
                            "resources": {{"app-image": {{"type": "oci-image", "rock": "go-app"}}}},
                            "builds": [{{
                                "arch": architecture, "base": "ubuntu@24.04",
                                "path": "build/go-k8s.charm",
                            }}],
                        }}],
                        "rocks": [{{
                            "name": "go-app", "rockcraft-yaml": "rockcraft.yaml",
                            "builds": [{{
                                "arch": architecture, "image": "go-app:built",
                                "file": "build/go-app.rock",
                            }}],
                        }}],
                    }}
                    path = build / "artifacts.build.yaml"
                    path.write_text(yaml.safe_dump(manifest))
                    return path

                def push(directory, *, missing_registry):
                    assert directory == root
                    assert missing_registry == "deploy"
                    EVENTS.append(("images",))
                    path = root / "build/artifacts.build.yaml"
                    manifest = yaml.safe_load(path.read_text())
                    image = "registry.test/go-app:built"
                    manifest["rocks"][0]["builds"][0]["image"] = image
                    path.write_text(yaml.safe_dump(manifest))
                    return [image]

                with pytest.MonkeyPatch.context() as patch:
                    patch.setenv("OPCLI_DEFER_ARTIFACTS", "1")
                    patch.setenv("GITHUB_ACTIONS", "true")
                    patch.setenv("GITHUB_RUN_ID", "123")
                    patch.setenv("GITHUB_REPOSITORY", "canonical/paas-charm")
                    patch.setenv("OPCLI_FETCH_WAIT_TIMEOUT", "17")
                    patch.delenv("OPCLI_ARTIFACTS_BUILD_YAML", raising=False)
                    patch.setattr(artifact_preparation, "artifacts_fetch", fetch)
                    patch.setattr(artifact_preparation, "provision_load", push)
                    yield
        """,
    )
    pytester.makepyfile("""
        import pytest
        from conftest import EVENTS, FAILED_BUILD
        def test_plugin(request):
            if FAILED_BUILD:
                with pytest.raises(RuntimeError, match="artifact build failed"):
                    request.getfixturevalue("go_app")
                assert not any(event[0] in ("app", "images") for event in EVENTS)
            else:
                assert request.getfixturevalue("go_app").name == "go-k8s"
                assert request.getfixturevalue("rock_images")["go-app"] == "registry.test/go-app:built"
                assert request.getfixturevalue("charm_paths")["go-k8s"].is_file()
                assert request.getfixturevalue("opcli_artifacts").rocks
                assert request.getfixturevalue("resource_images")["app-image"] == "registry.test/go-app:built"
                kinds = [event[0] for event in EVENTS]
                assert kinds.count("artifact-wait") == 1
                assert kinds.count("images") == 1
                assert kinds.index("images") < kinds.index("app")
        """)
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


@pytest.mark.parametrize("ci", [False, True])
def test_missing_charm_fallback(monkeypatch, tmp_path, tmp_path_factory, ci):
    """Deferred CI must fail missing artifacts; local mode retains packing."""
    monkeypatch.setenv("OPCLI_DEFER_ARTIFACTS", "1")
    monkeypatch.setenv("GITHUB_ACTIONS", "true" if ci else "false")
    pack = Mock()
    monkeypatch.setattr(fixtures.subprocess, "run", pack)
    monkeypatch.setattr(fixtures, "inject_venv", Mock())
    charm = tmp_path / "flask-k8s_ubuntu.charm"
    charm.write_bytes(b"packed")
    if ci:
        with pytest.raises(FileNotFoundError, match="flask-k8s charm not found"):
            fixtures.build_charm_file({}, "flask", tmp_path_factory, charm_location=tmp_path)
        pack.assert_not_called()
    else:
        result = fixtures.build_charm_file({}, "flask", tmp_path_factory, charm_location=tmp_path)
        assert result.read_bytes() == b"packed"
        assert result != charm
        pack.assert_called_once()


def test_prebuilt_copy_and_injection(monkeypatch, tmp_path, tmp_path_factory):
    """Mutations are applied to a private copy, never the shared build artifact."""
    charm = tmp_path / "flask.charm"
    charm.write_bytes(b"original")
    pack = Mock()
    monkeypatch.setattr(fixtures.subprocess, "run", pack)
    monkeypatch.setattr(
        fixtures, "inject_venv", lambda path, source: pathlib.Path(path).write_bytes(b"injected")
    )
    result = fixtures.build_charm_file({"flask-k8s": charm}, "flask", tmp_path_factory)
    assert charm.read_bytes() == b"original"
    assert result.read_bytes() == b"injected"
    pack.assert_not_called()
