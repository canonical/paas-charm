# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Deprecated Flask Charm service.

This module can be removed when paas_charm>=2.0.

It has to be maintained for the life cycle of bases 22.04 and 24.04.
"""

import paas_charm.flask.charm


class Charm(paas_charm.flask.charm.Charm):
    """Deprecated Flask charm."""
