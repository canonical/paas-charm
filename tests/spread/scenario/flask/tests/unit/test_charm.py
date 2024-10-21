# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Smoke scenario test for Flask."""


import scenario
import scenario.errors
from charm import FlaskHelloWorldCharm


def test_smoke():
    """The only goal of this test is a smoke test, that is, that the charm does not raise."""
    ctx = scenario.Context(FlaskHelloWorldCharm)
    container = scenario.Container(
        name='flask-app',
        can_connect=True,
    )
    state_in = scenario.State(containers={container})
    out = ctx.run(
        ctx.on.pebble_ready(container),
        state_in,
    )
    assert type(out.unit_status) in (scenario.WaitingStatus, scenario.BlockedStatus)
