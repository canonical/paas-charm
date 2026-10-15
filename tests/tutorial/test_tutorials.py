# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fast tutorial checks; these do not build rocks, deploy charms or contact guests."""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
FIXTURES = DOCS / "tutorial/code-26-04"
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
    mapping = yaml.safe_load((fixtures / "greeting_paas_config.yaml").read_text())
    assert mapping["config"]["options"]["greeting"]["env-var"] == "GREETING_VAR"

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


def test_manual_suite_is_isolated():
    """Keep live tutorial deployments out of existing automatic integration jobs."""
    config = yaml.safe_load((ROOT / "spread.yaml").read_text())
    suite = config["suites"]["docs/tutorial/code-26-04/"]
    assert suite["manual"] is True
    assert suite["backends"] == ["tutorial"]
    assert config["integration-suites"]["tests/integration/"]["backends"] == ["integration-test"]


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
