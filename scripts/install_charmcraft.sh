#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -ex

sudo snap install charmcraft --classic --channel=latest/edge

# Verify
charmcraft version
