#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Django Charm service."""

import logging
import typing

import ops

import paas_charm.django
from paas_charm.charm import PaasCharm

logger = logging.getLogger(__name__)


class DjangoCharm(paas_charm.django.Charm):
    """Django Charm service."""

    def __init__(self, *args: typing.Any) -> None:
        """Initialize the instance.

        Args:
            args: passthrough to CharmBase.
        """
        super().__init__(*args)

    def is_ready(self) -> bool:
        """Check if the charm is ready to start the workload application.

        Unlike the library default, a database integration is not required:
        this example can serve non-database endpoints without one. Database
        migrations are skipped when no database is related.

        Returns:
            True if the charm is ready to start the workload application.
        """
        return PaasCharm.is_ready(self)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(DjangoCharm)
