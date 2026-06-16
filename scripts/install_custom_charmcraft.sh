#!/bin/bash
set -ex

python3 -m venv /tmp/charmcraft-venv
/tmp/charmcraft-venv/bin/pip install --upgrade pip
/tmp/charmcraft-venv/bin/pip install \
    "git+https://github.com/alithethird/charmcraft@feat/extension-dispatch"

# Place in /usr/local/bin so it takes precedence over snap-installed charmcraft
# (useful for local runs where GITHUB_PATH is not available).
sudo ln -sf /tmp/charmcraft-venv/bin/charmcraft /usr/local/bin/charmcraft

# In GitHub Actions, prepend the fork's venv bin to PATH so it beats the
# `snap install charmcraft` step that the reusable workflow runs afterwards.
# Entries written to $GITHUB_PATH are placed at the front of PATH for every
# subsequent step and action in the job, ahead of /usr/local/bin and /snap/bin.
if [ -n "${GITHUB_PATH:-}" ]; then
  echo "/tmp/charmcraft-venv/bin" >> "$GITHUB_PATH"
fi

# The pip-installed fork (charmcraft 3.x) must build on the host rather than
# inside LXD.  operator-workflows already sets this, but write it explicitly as
# insurance so the fork respects the same build environment.
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "CRAFT_BUILD_ENVIRONMENT=host" >> "$GITHUB_ENV"
fi

# Verify
which charmcraft
charmcraft version
