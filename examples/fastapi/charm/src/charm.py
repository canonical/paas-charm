#!/usr/bin/env python3

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""FastAPI Charm service."""

import typing

import ops

import paas_charm.fastapi


class FastAPICharm(paas_charm.fastapi.Charm):
    """FastAPI Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(FastAPICharm)
