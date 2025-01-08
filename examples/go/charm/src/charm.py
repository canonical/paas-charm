#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go Charm service."""

import typing

import ops

import paas_charm.go


class GoCharm(paas_charm.go.Charm):
    """Go Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(GoCharm)
