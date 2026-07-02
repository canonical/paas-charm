# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for custom integration tests.

Provides:
- build_stub_charm(): helper that writes a minimal charm to a tmp dir and packs it
- Provider/requirer stubs for bespoke interfaces (ophelia-interface,
  garm_configurator_v0, github_runner_planner_v0)
- Provider charms from Charmhub (temporal-k8s, nginx-ingress-integrator)
- A go-k8s variant with garm-configurator declared required (for lifecycle tests)
"""

import logging
import pathlib
import subprocess
import textwrap

import jubilant
import pytest
import yaml

from tests.integration.conftest import build_charm_file, deploy_postgresql, generate_app_fixture
from tests.integration.types import App

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent.parent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------

FLASK_PORT = 8000
FASTAPI_PORT = 8080
GO_PORT = 8080
EXPRESSJS_PORT = 8080


# ---------------------------------------------------------------------------
# Stub charm builder
# ---------------------------------------------------------------------------

def build_stub_charm(
    stub_name: str,
    charmcraft_extra: dict,
    src_py: str,
    tmp_path_factory,
) -> pathlib.Path:
    """Write a minimal stub charm, pack it, and return the .charm path.

    Args:
        stub_name: Base name used for tmp directory and app name.
        charmcraft_extra: Keys to merge into the minimal charmcraft.yaml
            (typically ``provides`` or ``requires``).
        src_py: Python source of src/charm.py.
        tmp_path_factory: pytest tmp_path_factory fixture.

    Returns:
        Absolute path to the packed .charm file.
    """
    charm_dir = tmp_path_factory.mktemp(stub_name)
    (charm_dir / "src").mkdir()
    (charm_dir / "src" / "charm.py").write_text(textwrap.dedent(src_py))

    charmcraft: dict = {
        "name": stub_name,
        "summary": f"Stub charm for {stub_name} integration tests",
        "description": f"Minimal stub providing or requiring the {stub_name} relation",
        "base": "ubuntu@24.04",
        "platforms": {"amd64": {}},
        "type": "charm",
        "parts": {
            "charm": {
                "plugin": "charm",
            }
        },
    }
    charmcraft.update(charmcraft_extra)
    (charm_dir / "charmcraft.yaml").write_text(yaml.dump(charmcraft))

    subprocess.run(
        ["charmcraft", "pack", "--verbosity=brief"],
        cwd=charm_dir,
        check=True,
        capture_output=False,
    )
    charms = list(charm_dir.glob("*.charm"))
    assert charms, f"No .charm produced in {charm_dir}"
    return charms[0].absolute()


# ---------------------------------------------------------------------------
# temporal-k8s provider (from Charmhub)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", name="temporal_k8s_app")
def temporal_k8s_app_fixture(juju: jubilant.Juju) -> App:
    """Deploy temporal-k8s as the temporal-host-info provider.

    temporal-k8s needs postgresql + TLS certificates to reach Active.
    """
    app_name = "temporal-k8s"
    if app_name not in juju.status().apps:
        deploy_postgresql(juju)
        juju.deploy(
            "temporal-k8s",
            channel="latest/edge",
            trust=True,
            config={"services": "frontend:7233,history:7234,matching:7235,worker:7236"},
        )
        juju.deploy("self-signed-certificates", app="temporal-certs", channel="1/edge")
        juju.integrate(app_name, "postgresql-k8s:database")
        juju.integrate(f"{app_name}:certificates", "temporal-certs:certificates")

    juju.wait(
        lambda status: status.apps[app_name].is_active,
        timeout=15 * 60,
    )
    return App(app_name)


# ---------------------------------------------------------------------------
# nginx-ingress-integrator (from Charmhub)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", name="nginx_ingress_integrator_app")
def nginx_ingress_integrator_app_fixture(juju: jubilant.Juju) -> App:
    """Deploy nginx-ingress-integrator as the nginx-route provider."""
    app_name = "nginx-ingress-integrator"
    if app_name not in juju.status().apps:
        juju.deploy(
            app_name,
            channel="latest/stable",
            trust=True,
            config={
                "service-hostname": "nginx.test",
                "service-name": "expressjs-k8s",
            },
        )

    # nginx-ingress-integrator waits for a related charm; active or waiting is fine
    juju.wait(
        lambda status: (
            status.apps[app_name].is_active or status.apps[app_name].is_waiting
        ),
        timeout=5 * 60,
    )
    return App(app_name)


# ---------------------------------------------------------------------------
# Ophelia-server stub (provides ophelia-interface)
# ---------------------------------------------------------------------------

_OPHELIA_SERVER_STUB_SRC = """
    import ops

    class OpheliaServerStub(ops.CharmBase):
        def __init__(self, *args):
            super().__init__(*args)
            self.framework.observe(
                self.on["ophelia-server"].relation_joined, self._on_joined
            )
            self.framework.observe(
                self.on["ophelia-server"].relation_changed, self._on_joined
            )

        def _on_joined(self, event):
            event.relation.data[self.app]["server_address"] = "10.0.0.42:50051"
            event.relation.data[self.app]["server_version"] = "1"
            self.unit.status = ops.ActiveStatus("ready")

    ops.main(OpheliaServerStub)
"""


@pytest.fixture(scope="module", name="ophelia_server_stub")
def ophelia_server_stub_fixture(juju: jubilant.Juju, tmp_path_factory) -> App:
    """Deploy a stub charm that provides the ophelia-interface relation."""
    app_name = "ophelia-server-stub"
    if app_name not in juju.status().apps:
        charm_file = build_stub_charm(
            stub_name=app_name,
            charmcraft_extra={
                "provides": {
                    "ophelia-server": {"interface": "ophelia-interface"}
                }
            },
            src_py=_OPHELIA_SERVER_STUB_SRC,
            tmp_path_factory=tmp_path_factory,
        )
        juju.deploy(charm=charm_file, app=app_name)

    juju.wait(lambda status: status.apps[app_name].is_active, timeout=5 * 60)
    return App(app_name)


# ---------------------------------------------------------------------------
# Garm-configurator stub (provides garm_configurator_v0)
# ---------------------------------------------------------------------------

_GARM_CONFIGURATOR_STUB_SRC = """
    import ops

    OPENSTACK_DATA = {
        "openstack_auth_url":          "https://keystone.example.com:5000/v3",
        "openstack_username":          "garm-user",
        "openstack_password":          "test-pass",
        "openstack_project_name":      "test-project",
        "openstack_user_domain_name":  "Default",
        "openstack_project_domain_name": "Default",
        "openstack_region_name":       "RegionOne",
        "openstack_network":           "test-net",
        "name":                        "test-scaleset",
        "provider_name":               "stub-provider",
        "image_id":                    "img-1234",
        "flavor":                      "m1.small",
        "os_arch":                     "x64",
        "max_runner":                  "5",
        "min_idle_runner":             "0",
        "org":                         "test-org",
    }

    class GarmConfiguratorStub(ops.CharmBase):
        def __init__(self, *args):
            super().__init__(*args)
            for event_name in (
                "relation_joined",
                "relation_changed",
            ):
                self.framework.observe(
                    self.on["garm-configurator"][event_name], self._on_relation
                )

        def _on_relation(self, event):
            unit_data = event.relation.data[self.unit]
            for key, value in OPENSTACK_DATA.items():
                unit_data[key] = value
            self.unit.status = ops.ActiveStatus("configured")

    ops.main(GarmConfiguratorStub)
"""


@pytest.fixture(scope="module", name="garm_configurator_stub")
def garm_configurator_stub_fixture(juju: jubilant.Juju, tmp_path_factory) -> App:
    """Deploy a stub charm that provides the garm-configurator relation."""
    app_name = "garm-configurator-stub"
    if app_name not in juju.status().apps:
        charm_file = build_stub_charm(
            stub_name=app_name,
            charmcraft_extra={
                "provides": {
                    "garm-configurator": {"interface": "garm_configurator_v0"}
                }
            },
            src_py=_GARM_CONFIGURATOR_STUB_SRC,
            tmp_path_factory=tmp_path_factory,
        )
        juju.deploy(charm=charm_file, app=app_name)

    juju.wait(lambda status: status.apps[app_name].is_active, timeout=5 * 60)
    return App(app_name)


# ---------------------------------------------------------------------------
# Planner requirer stub (requires github_runner_planner_v0)
# ---------------------------------------------------------------------------

_PLANNER_REQUIRER_STUB_SRC = """
    import ops

    class PlannerRequirerStub(ops.CharmBase):
        def __init__(self, *args):
            super().__init__(*args)
            self.framework.observe(
                self.on["planner"].relation_joined, self._on_joined
            )
            self.framework.observe(
                self.on["planner"].relation_changed, self._on_changed
            )

        def _on_joined(self, event):
            event.relation.data[self.app]["flavor"] = "test-flavor"
            self.unit.status = ops.ActiveStatus("joined")

        def _on_changed(self, event):
            # Just stay active when data arrives
            self.unit.status = ops.ActiveStatus("ready")

    ops.main(PlannerRequirerStub)
"""


@pytest.fixture(scope="module", name="planner_requirer_stub")
def planner_requirer_stub_fixture(juju: jubilant.Juju, tmp_path_factory) -> App:
    """Deploy a stub charm that requires the planner relation."""
    app_name = "planner-stub"
    if app_name not in juju.status().apps:
        charm_file = build_stub_charm(
            stub_name=app_name,
            charmcraft_extra={
                "requires": {
                    "planner": {"interface": "github_runner_planner_v0"}
                }
            },
            src_py=_PLANNER_REQUIRER_STUB_SRC,
            tmp_path_factory=tmp_path_factory,
        )
        juju.deploy(charm=charm_file, app=app_name)

    juju.wait(lambda status: status.apps[app_name].is_active, timeout=5 * 60)
    return App(app_name)


# ---------------------------------------------------------------------------
# go-k8s variant with garm-configurator required (optional=False)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", name="go_app_garm")
def go_app_garm_fixture(
    juju: jubilant.Juju,
    charm_paths: dict[str, pathlib.Path],
    go_app_image: str,
    tmp_path_factory,
) -> App:
    """Deploy go-k8s with garm-configurator declared required.

    Uses charm_dict to override garm-configurator optional flag to False so
    the charm enters Waiting/Blocked when the relation is absent, enabling
    lifecycle tests (blocked → active → blocked).
    """
    app_name = "go-k8s-garm"
    if app_name not in juju.status().apps:
        charm_dict = {
            "requires": {
                "garm-configurator": {
                    "interface": "garm_configurator_v0",
                    "optional": False,
                },
                # Keep existing optional relations so the override is additive
                "traefik-route": {
                    "interface": "traefik_route",
                    "optional": True,
                    "limit": 1,
                },
                "planner": {
                    "interface": "github_runner_planner_v0",
                    "optional": True,
                },
            }
        }
        charm_file = build_charm_file(
            charm_paths, "go", tmp_path_factory, charm_dict=charm_dict
        )
        juju.deploy(
            charm=charm_file,
            app=app_name,
            resources={"app-image": go_app_image},
            config={"metrics-port": 8081},
        )
        # Connect to postgresql (required by go charm)
        deploy_postgresql(juju)
        try:
            juju.integrate(app_name, "postgresql-k8s:database")
        except jubilant.CLIError as err:
            if "already exists" not in err.stderr:
                raise

    # Wait until postgresql is active; the app itself will be blocked/waiting
    # because garm-configurator is required but not yet related.
    juju.wait(
        lambda status: status.apps.get("postgresql-k8s", {}) and
        status.apps["postgresql-k8s"].is_active,
        timeout=10 * 60,
    )
    # Give the app a moment to settle into blocked/waiting state
    juju.wait(
        lambda status: not status.apps[app_name].is_active
        if app_name in status.apps else False,
        timeout=5 * 60,
    )
    return App(app_name)
