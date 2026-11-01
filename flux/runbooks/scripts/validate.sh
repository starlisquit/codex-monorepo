#!/usr/bin/env bash
set -euo pipefail
repo_root=$(git rev-parse --show-toplevel)
kustomize_bin=${KUSTOMIZE_BIN:-kustomize}
command -v "$kustomize_bin" >/dev/null
python3 "$repo_root/flux/runbooks/scripts/validate-platform.py"
count=0
while IFS= read -r -d '' manifest; do
  "$kustomize_bin" build "$(dirname "$manifest")" >/dev/null
  count=$((count + 1))
done < <(find "$repo_root/flux/infrastructure" "$repo_root/flux/clusters" -name kustomization.yaml -print0)
echo "Validated $count Kustomize builds"
git -C "$repo_root" diff --check
