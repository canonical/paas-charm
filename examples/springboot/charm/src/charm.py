#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Spring Boot Charm service."""

import typing

import ops

import paas_charm.springboot


class SpringBootCharm(paas_charm.springboot.Charm):
    """Spring Boot Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)


if __name__ == "__main__":
    ops.main.main(SpringBootCharm)
