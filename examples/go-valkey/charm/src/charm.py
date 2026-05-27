#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Go Valkey Charm service."""

import typing

import ops

import paas_charm.go


class GoValkeyCharm(paas_charm.go.Charm):
    """Go Valkey Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(GoValkeyCharm)
