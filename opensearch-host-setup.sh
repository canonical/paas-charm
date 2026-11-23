#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

# The OpenSearch machine charm checks these kernel settings. Its LXD containers share them with
# the host, so the charm can't set them itself.

set -euo pipefail

if [ "$(sysctl -n vm.max_map_count)" -lt 262144 ]; then
    sudo sysctl -w vm.max_map_count=262144
fi
if [ "$(sysctl -n vm.swappiness)" -gt 1 ]; then
    sudo sysctl -w vm.swappiness=0
fi
