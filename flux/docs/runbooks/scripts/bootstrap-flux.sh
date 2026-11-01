#!/usr/bin/env bash
# Applies manifests committed to the selected Git branch. No credential is needed
# for this public repository; private repositories require a Git source Secret.
set -euo pipefail
repo_root=$(git rev-parse --show-toplevel)
cluster_dir=${1:?Usage: pass the explicit flux/clusters/<run-folder> path}
for executable in kubectl flux; do command -v "$executable" >/dev/null; done
flux check --pre
kubectl apply --server-side --field-manager=bootstrap \
  -f "$repo_root/flux/bootstrap/flux-system/gotk-components.yaml"
# Include cluster-specific controller patches in the initial installation.
kubectl apply --server-side --field-manager=bootstrap -k "$repo_root/$cluster_dir/flux-system"
kubectl -n flux-system rollout status deployment/source-controller --timeout=3m
kubectl -n flux-system rollout status deployment/kustomize-controller --timeout=3m
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization flux-system --timeout=3m
flux get kustomizations -A
