# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""OpenFGA related constants."""

# Hardcoded store name for the charm.
# Store names are not unique on OpenFGA, there can be multiple stores with the same name.
# The relation returns a store id, which is unique.
STORE_NAME = "app-store"
