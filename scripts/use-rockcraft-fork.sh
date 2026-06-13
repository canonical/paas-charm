#!/bin/bash
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
# Install rockcraft from alithethird fork (feat/bump-gunicorn-statsd).
# Installs to /usr/local/bin which precedes /snap/bin in PATH on GitHub runners,
# so this version is used for rock builds even after the snap install step runs.
set -ex

FORK_URL="git+https://github.com/alithethird/rockcraft@feat/bump-gunicorn-statsd"

sudo pip install --break-system-packages \
  --ignore-installed \
  "${FORK_URL}"

# Verify the installed version is from our fork
rockcraft --version || /usr/local/bin/rockcraft --version
