#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -e

# shellcheck source=/dev/null
. /etc/os-release
if [ "$VERSION_ID" != "26.04" ]; then
    echo "Tutorial walkthroughs require a disposable Ubuntu 26.04 guest." >&2
    exit 1
fi

for tool in juju k8s rockcraft charmcraft; do
    case "$tool" in
        juju) options=(--channel=3.6/stable) ;;
        k8s) options=(--channel=1.34-classic/stable --classic) ;;
        *) options=(--channel=latest/edge --classic) ;;
    esac
    if snap list "$tool" >/dev/null 2>&1; then
        sudo snap refresh "$tool" "${options[@]}"
    else
        sudo snap install "$tool" "${options[@]}"
    fi
done

if ! snap list lxd >/dev/null 2>&1; then
    sudo snap install lxd
fi
sudo usermod -aG lxd "$(id -un)"
sudo lxd init --auto
sudo lxc network set lxdbr0 ipv6.address none
