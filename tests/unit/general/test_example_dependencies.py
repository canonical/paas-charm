# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Consistency checks between root and example charm dependencies."""

import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
ROOT_PYPROJECT = PROJECT_ROOT / "pyproject.toml"
EXAMPLE_PYPROJECTS = sorted(PROJECT_ROOT.glob("examples/*/charm/pyproject.toml"))


def _project_dependencies(pyproject_path):
    """Return the project dependencies declared in a pyproject.toml file."""
    with pyproject_path.open("rb") as file:
        return set(tomllib.load(file)["project"]["dependencies"])


def test_example_pyprojects_are_discovered():
    """
    arrange: given the repository layout.
    act: when example charm pyproject.toml files are discovered.
    assert: at least one example charm pyproject.toml is found.
    """
    assert EXAMPLE_PYPROJECTS


@pytest.mark.parametrize(
    "example_pyproject",
    EXAMPLE_PYPROJECTS,
    ids=lambda path: path.parent.parent.name,
)
def test_example_dependencies_match_root(example_pyproject):
    """
    arrange: given the root pyproject.toml and an example charm pyproject.toml.
    act: when the project dependencies are read from both files.
    assert: the example charm declares the same dependencies as the root project.
    """
    expected = _project_dependencies(ROOT_PYPROJECT)
    actual = _project_dependencies(example_pyproject)
    assert actual == expected, (
        f"{example_pyproject.relative_to(PROJECT_ROOT)} is out of sync with pyproject.toml. "
        f"Missing: {sorted(expected - actual)}. Unexpected: {sorted(actual - expected)}."
    )
