#!/usr/bin/env bash
set -euo pipefail
repo_root=$(git rev-parse --show-toplevel)
kustomize_bin=${KUSTOMIZE_BIN:-kustomize}
command -v "$kustomize_bin" >/dev/null
python3 "$repo_root/flux/docs/runbooks/scripts/validate-platform.py"
python3 "$repo_root/flux/docs/runbooks/scripts/validate-compositions.py"
python3 "$repo_root/flux/docs/runbooks/scripts/validate-external-secrets.py"
count=0
while IFS= read -r -d '' manifest; do
  # Every Component is validated in owner compositions by validate-compositions.py.
  kind=$(python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["kind"])' "$manifest")
  if [[ "$kind" == "Component" ]]; then
    continue
  fi
  "$kustomize_bin" build "$(dirname "$manifest")" >/dev/null
  count=$((count + 1))
done < <(find "$repo_root/flux/infrastructure" "$repo_root/flux/bootstrap" "$repo_root/flux/clusters" "$repo_root/flux/policies" "$repo_root/flux/dashboards" -name kustomization.yaml -print0)
echo "Validated $count Kustomize builds"
git -C "$repo_root" diff --check
