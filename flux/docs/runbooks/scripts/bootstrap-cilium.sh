#!/usr/bin/env bash
# Run from a checkout on the new cluster's dev-machine.
set -euo pipefail
repo_root=$(git rev-parse --show-toplevel)
cluster_dir=${1:?Usage: pass the explicit flux/clusters/<run-folder> path}
api_host=${2:-172.16.0.2}
api_port=${3:-6443}
for executable in kubectl helm; do command -v "$executable" >/dev/null; done
kubectl cluster-info
if kubectl -n kube-system get daemonset kube-proxy >/dev/null 2>&1; then
  echo 'Existing kube-proxy detected. Follow flux/docs/runbooks/bootstrap/02-cilium-and-flux.md before migrating.' >&2
  exit 1
fi
bootstrap_values=$(mktemp)
trap 'rm -f "$bootstrap_values"' EXIT
cat > "$bootstrap_values" <<'YAML'
gatewayAPI:
  enabled: false
prometheus:
  serviceMonitor:
    enabled: false
operator:
  prometheus:
    serviceMonitor:
      enabled: false
envoy:
  prometheus:
    serviceMonitor:
      enabled: false
hubble:
  # Central PKI and its CRDs do not exist until Flux installs cert-manager.
  enabled: false
  tls:
    auto:
      enabled: false
  ui:
    enabled: false
  relay:
    enabled: false
    prometheus:
      serviceMonitor:
        enabled: false
  metrics:
    serviceMonitor:
      enabled: false
tls:
  caBundle:
    enabled: false
YAML
helm repo add cilium https://helm.cilium.io/ --force-update
helm repo update cilium
helm upgrade --install cilium cilium/cilium --version 1.20.4 \
  --namespace kube-system \
  -f "$repo_root/flux/infrastructure/networking/cilium/values.yaml" \
  -f "$repo_root/$cluster_dir/cilium/values.yaml" \
  -f "$bootstrap_values" \
  --set-string "k8sServiceHost=$api_host" --set "k8sServicePort=$api_port" \
  --wait --timeout=10m
kubectl wait --for=condition=Ready nodes --all --timeout=2m
