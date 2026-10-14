#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

S3_ACCESS_KEY="my-lovely-key"
S3_SECRET_KEY="this-is-very-secret"
S3_BUCKET="paas-bucket"
S3_PORT=7480

log() {
    echo "[s3-installation $(date -u +%H:%M:%S)] $*"
}

on_error() {
    log "FAILED at line $1: $2"
    sudo microceph status || true
    sudo snap services microceph || true
    sudo ss -tlnp || true
}

trap 'on_error "${LINENO}" "${BASH_COMMAND}"' ERR

if snap list microceph >/dev/null 2>&1; then
    if sudo microceph.radosgw-admin user info --uid ci-user >/dev/null 2>&1 && \
        curl -sf "http://127.0.0.1:${S3_PORT}/${S3_BUCKET}" \
            --aws-sigv4 "aws:amz:us-east-1:s3" \
            --user "${S3_ACCESS_KEY}:${S3_SECRET_KEY}" >/dev/null; then
        log "Reusing existing MicroCeph RGW setup"
        exit 0
    fi
    log "An incomplete MicroCeph installation already exists"
    exit 1
fi

log "Installing MicroCeph"
sudo snap install microceph --channel squid/stable
log "Bootstrapping MicroCeph"
sudo microceph cluster bootstrap
log "Adding loopback OSDs"
sudo microceph disk add loop,1G,3
log "Enabling RGW on port ${S3_PORT}"
sudo microceph enable rgw --port "${S3_PORT}" --wait

log "Waiting for RGW"
curl --connect-timeout 2 --max-time 5 --retry 30 --retry-delay 4 --retry-all-errors \
    -s -o /dev/null "http://127.0.0.1:${S3_PORT}"

log "Creating S3 user"
sudo microceph.radosgw-admin user create \
    --uid ci-user \
    --display-name "CI User" \
    --access-key "${S3_ACCESS_KEY}" \
    --secret-key "${S3_SECRET_KEY}"

log "Creating bucket ${S3_BUCKET}"
curl -sf -X PUT "http://127.0.0.1:${S3_PORT}/${S3_BUCKET}" \
    --aws-sigv4 "aws:amz:us-east-1:s3" \
    --user "${S3_ACCESS_KEY}:${S3_SECRET_KEY}"