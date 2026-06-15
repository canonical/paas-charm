#!/bin/bash
set -ex

python3 -m venv /tmp/charmcraft-venv
/tmp/charmcraft-venv/bin/pip install --upgrade pip
/tmp/charmcraft-venv/bin/pip install \
    "git+https://github.com/alithethird/charmcraft@feat/extension-dispatch"

# Place in /usr/local/bin so it takes precedence over snap-installed charmcraft
sudo ln -sf /tmp/charmcraft-venv/bin/charmcraft /usr/local/bin/charmcraft

# Verify
which charmcraft
charmcraft version
