# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fast tutorial checks; these do not build rocks, deploy charms or contact guests."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
FIXTURES = DOCS / "tutorial/code-26-04"
SHARED_FIXTURES = DOCS / "reuse/tutorial/fixtures"
FRAMEWORKS = ("django", "expressjs", "fastapi", "flask", "go", "spring-boot")
PAGES = sorted((DOCS / "tutorial").glob("*-26-04.rst"))
RETRY = ROOT / "tests/tutorial/tools/retry"


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_framework_walkthrough(framework):
    """Check the preserved base, registry, lockfile, config and database contracts."""
    fixtures = FIXTURES / framework
    task = yaml.safe_load((fixtures / "task.yaml").read_text())
    script = task["execute"]
    for section in ("execute", "restore"):
        subprocess.run(["bash", "-n"], input=task[section], text=True, check=True)
    assert "--base ubuntu@26.04" in script
    assert "uv lock" in script
    assert "localhost:32000/" in script
    assert "$REGISTRY" not in script
    assert "greeting='Hi!'" in script
    assert ("16/edge" if framework == "django" else "14/edge") in script
    page_name = "express" if framework == "expressjs" else framework
    basename = f"kubernetes-charm-{page_name}-26-04"
    page = DOCS / f"tutorial/{basename}.rst"
    assert f".. _tutorial-{basename}:" in page.read_text()
    assert basename in (DOCS / "tutorial/ubuntu-26-04.rst").read_text()


@pytest.mark.parametrize("page", PAGES + [DOCS / "reuse/tutorial/setup_26_04.rst"])
def test_literalinclude_targets_and_markers(page):
    """Keep included files and snippet boundaries resolvable after migrations."""
    directives = re.finditer(
        r"^\.\. literalinclude:: (.+)\n((?:[ \t]+[^\n]*\n)*)",
        page.read_text(),
        re.MULTILINE,
    )
    for directive in directives:
        name, options = directive.groups()
        target = DOCS / name.lstrip("/") if name.startswith("/") else page.parent / name
        assert target.is_file(), (page, target)
        contents = target.read_text()
        start = re.search(r":start-after: (.+)", options)
        end = re.search(r":end-before: (.+)", options)
        if start:
            assert start[1] in contents, (page, target, start[1])
            contents = contents.split(start[1], 1)[1]
        if end:
            assert end[1] in contents, (page, target, end[1])
            contents = contents.split(end[1], 1)[0]
        assert contents.strip(), (page, target)


@pytest.mark.parametrize("framework,package", [("flask", "Flask"), ("fastapi", "FastAPI")])
def test_documented_python_versions(framework, package):
    """Check prose versions against the requirements used by the walkthrough."""
    requirements = (FIXTURES / framework / "requirements.txt").read_text()
    version = re.search(r"==([\d.]+)", requirements)[1]
    page = (DOCS / f"tutorial/kubernetes-charm-{framework}-26-04.rst").read_text()
    assert f"with {package} {version}." in page


def test_django_refresh_starts_at_project_root():
    """Prevent reader instructions from entering a nonexistent charm/charm directory."""
    page = (DOCS / "tutorial/kubernetes-charm-django-26-04.rst").read_text()
    assert "From the Django project root, ``~/django-tutorial``, run:" in page
    task = yaml.safe_load((FIXTURES / "django/task.yaml").read_text())["execute"]
    snippet = task.split("# [docs:refresh-deployment]\n", 1)[1]
    assert snippet.lstrip().startswith("cd charm\n")


def test_registry_manifest_is_downloaded_not_embedded():
    """Keep the shared setup concise while retaining the repository manifest."""
    setup = (DOCS / "reuse/tutorial/setup_26_04.rst").read_text()
    assert ".. literalinclude:: /reuse/tutorial/registry_26_04.yaml" not in setup
    assert "curl --fail --location --output registry.yaml" in setup
    assert (
        "https://raw.githubusercontent.com/canonical/paas-charm/main/"
        "docs/reuse/tutorial/registry_26_04.yaml"
    ) in setup
    assert (DOCS / "reuse/tutorial/registry_26_04.yaml").is_file()
    bootstrap = (DOCS / "reuse/tutorial/bootstrap_26_04.sh").read_text()
    assert "sudo k8s kubectl apply -f registry.yaml" in bootstrap


def test_vm_address_placeholder():
    """Keep reader commands independent of shell variables and example-specific IPs."""
    setup = (DOCS / "reuse/tutorial/setup_26_04.rst").read_text()
    assert "multipass info charm-dev" in setup
    assert 'sudo k8s set load-balancer.cidrs="<VM_IP>/32"' in setup
    for page in PAGES:
        text = page.read_text()
        assert "NODE_IP" not in text
        if page.name.startswith("kubernetes-charm-"):
            assert ':80:"<VM_IP>"' in text


def test_manual_suite_is_isolated():
    """Keep live tutorial deployments out of existing automatic integration jobs."""
    config = yaml.safe_load((ROOT / "spread.yaml").read_text())
    suite = config["suites"]["docs/tutorial/code-26-04/"]
    assert suite["manual"] is True
    assert suite["backends"] == ["tutorial"]
    assert config["integration-suites"]["tests/integration/"]["backends"] == ["integration-test"]


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_shared_fixtures_are_staged_for_each_task(framework, tmp_path):
    """Stage the original filenames before task scripts move them to their app projects."""
    shared = tmp_path / "docs/reuse/tutorial/fixtures"
    shutil.copytree(SHARED_FIXTURES, shared)
    task_path = f"docs/tutorial/code-26-04/{framework}"
    task = tmp_path / task_path
    shutil.copytree(FIXTURES / framework, task)
    config = yaml.safe_load((ROOT / "spread.yaml").read_text())
    script = config["suites"]["docs/tutorial/code-26-04/"]["prepare-each"]
    subprocess.run(
        ["bash", "-eu", "-c", script],
        env={**os.environ, "SPREAD_PATH": str(tmp_path), "SPREAD_TASK": task_path},
        check=True,
    )
    assert not (task / "paas-config.yaml").exists()
    assert not (task / "greeting_paas_config.yaml").exists()
    if framework in ("expressjs", "go"):
        for name in ("visitors_migrate.sh", "visitors_rockcraft.yaml"):
            assert (task / name).read_bytes() == (shared / name).read_bytes()
    elif framework == "spring-boot":
        assert not (task / "visitors_migrate.sh").exists()


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_task_generates_packaged_configuration(framework, tmp_path):
    """Execute the included commands and verify initial and replacement configurations."""
    script = yaml.safe_load((FIXTURES / framework / "task.yaml").read_text())["execute"]
    port = 8000 if framework in ("django", "fastapi", "flask") else 8080
    expected = f"port: {port}\n"
    page_name = "express" if framework == "expressjs" else framework
    page = (DOCS / f"tutorial/kubernetes-charm-{page_name}-26-04.rst").read_text()
    for marker in ("create-paas-config", "configure-greeting"):
        snippet = script.split(f"# [docs:{marker}]\n", 1)[1]
        snippet = snippet.split(f"# [docs:{marker}-end]", 1)[0]
        assert f":start-after: [docs:{marker}]" in page
        assert f":end-before: [docs:{marker}-end]" in page
        subprocess.run(["bash", "-eu", "-c", snippet], cwd=tmp_path, check=True)
        if marker == "configure-greeting":
            expected += "config:\n  options:\n    greeting:\n      env-var: GREETING_VAR\n"
        assert (tmp_path / "paas-config.yaml").read_text() == expected


@pytest.mark.parametrize(
    "script",
    [
        DOCS / "reuse/tutorial/bootstrap_26_04.sh",
        ROOT / "tests/tutorial/prepare.sh",
        RETRY,
    ],
)
def test_shared_shell_syntax(script):
    """Parse shared scripts without executing their provisioning commands."""
    subprocess.run(["bash", "-n", str(script)], check=True)


@pytest.mark.parametrize(
    "arguments,expected",
    [
        (["-n", "2", "--wait", "0", "true"], 0),
        (["-n", "2", "--wait", "0", "bash", "-c", "exit 7"], 7),
        (["-n", "0", "--wait", "0", "true"], 2),
        (["-n", "2", "--wait", "invalid", "true"], 2),
        ([], 2),
        (
            ["-n", "2", "--wait", "0", "bash", "-c", '[[ "$1" == "a b" ]]', "_", "a b"],
            0,
        ),
    ],
)
def test_retry_exit_status(arguments, expected):
    """Preserve command arguments and report failures rather than false successes."""
    result = subprocess.run([str(RETRY), *arguments], capture_output=True, check=False)
    assert result.returncode == expected


def test_retry_recovers(tmp_path):
    """Retry a transient failure without requiring network access."""
    marker = tmp_path / "attempted"
    subprocess.run(
        [
            str(RETRY),
            "-n",
            "2",
            "--wait",
            "0",
            "bash",
            "-c",
            'if test -f "$1"; then exit 0; else touch "$1"; exit 1; fi',
            "_",
            str(marker),
        ],
        check=True,
    )
    assert marker.is_file()
