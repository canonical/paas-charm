# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Utils unit tests."""


import ops
import pytest
from ops.testing import Harness


@pytest.mark.parametrize(
    "blocked_harness_fixture",
    ["flask_harness"],  # , "go_harness", "fastapi_harness", "django_harness"],
)
def test_non_optional_config(request, blocked_harness_fixture: Harness) -> None:
    blocked_harness = request.getfixturevalue(blocked_harness_fixture)

    assert isinstance(blocked_harness.model.unit.status, ops.model.BlockedStatus)
    assert "non-optional-test" in blocked_harness.model.unit.status.message

    blocked_harness.update_config({"non-optional-test": "something"})
    assert isinstance(blocked_harness.model.unit.status, ops.model.ActiveStatus)
    assert "non-optional-test" not in blocked_harness.model.unit.status.message
