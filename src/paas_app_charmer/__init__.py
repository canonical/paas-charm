# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Deprecated entrypoints for charms.

This module can be removed when paas_charm>=2.0.

It has to be maintained for the life cycle of bases 22.04 and 24.04.
"""

import warnings

warnings.warn("paas_app_charmer package is deprecated", DeprecationWarning, stacklevel=2)
