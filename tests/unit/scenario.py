# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared non-fixture helpers for Scenario unit tests."""

import pathlib

from examples.django.charm.src.charm import DjangoCharm
from examples.expressjs.charm.src.charm import ExpressJSCharm
from examples.fastapi.charm.src.charm import FastAPICharm
from examples.flask.charm.src.charm import FlaskCharm
from examples.go.charm.src.charm import GoCharm
from examples.springboot.charm.src.charm import SpringBootCharm
from tests.unit.test_charm.src.charm import TestCharm

PROJECT_ROOT = pathlib.Path(__file__).parents[2]
CHARM_ROOTS = {
    TestCharm: PROJECT_ROOT / "tests/unit/test_charm",
    FlaskCharm: PROJECT_ROOT / "examples/flask/charm",
    DjangoCharm: PROJECT_ROOT / "examples/django/charm",
    FastAPICharm: PROJECT_ROOT / "examples/fastapi/charm",
    GoCharm: PROJECT_ROOT / "examples/go/charm",
    ExpressJSCharm: PROJECT_ROOT / "examples/expressjs/charm",
    SpringBootCharm: PROJECT_ROOT / "examples/springboot/charm",
}
FRAMEWORKS = {
    FlaskCharm: "flask",
    DjangoCharm: "django",
    FastAPICharm: "fastapi",
    GoCharm: "go",
    ExpressJSCharm: "expressjs",
    SpringBootCharm: "spring-boot",
}


def charm_root(charm_type: type) -> pathlib.Path:
    """Return the explicit charm root for a test charm type."""
    return CHARM_ROOTS[charm_type]
