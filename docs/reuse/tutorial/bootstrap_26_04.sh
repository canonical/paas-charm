#!/bin/bash

set -e

# [docs:bootstrap-k8s]
sudo k8s bootstrap --timeout 10m
sudo k8s status --wait-ready --timeout 10m
sudo k8s enable local-storage
sudo k8s enable gateway
# [docs:bootstrap-k8s-end]

# [docs:enable-load-balancer]
sudo k8s enable load-balancer
sudo k8s kubectl wait --for=condition=Accepted gatewayclass/ck-gateway --timeout=5m
# [docs:enable-load-balancer-end]

# [docs:deploy-registry]
sudo k8s kubectl apply -f registry.yaml
sudo k8s kubectl rollout status deployment/registry \
  -n charm-tutorial-registry --timeout=5m
curl --fail --retry 30 --retry-connrefused --retry-delay 2 "http://localhost:32000/v2/"
# [docs:deploy-registry-end]

# [docs:bootstrap-juju]
mkdir -p ~/.local/share
sudo k8s config | juju add-k8s k8s --client
juju bootstrap k8s dev-controller --config bootstrap-timeout=600
# [docs:bootstrap-juju-end]
