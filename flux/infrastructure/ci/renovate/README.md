# Renovate

Namespaces are defined centrally in [the namespace bundle](../../namespaces/README.md).
Reconcile that foundation before this template; this directory does not create
its own namespace.

Official [Renovate chart](https://github.com/renovatebot/helm-charts), chart
`46.396.0` / Renovate `44.198.0`, from `https://docs.renovatebot.com/helm-charts`.
The directory uses the product spelling `renovate`.

The component creates namespace `ci` and an opt-in CronJob. It is not selected by
the full-platform overlay. Default schedule: 03:00 Europe/Istanbul daily.
`concurrencyPolicy: Forbid` prevents overlapping scheduled runs; Jobs have a
one-hour deadline and bounded history/retries. Manual Jobs can still overlap.

Create Secret `ci/renovate-credentials` containing `RENOVATE_TOKEN`, preferably a
dedicated GitLab bot token scoped to the explicit repositories and required API/
repository operations. A private dependency registry may need separate host rules
and credentials; do not place tokens in the ConfigMap or Git.

```sh
kubectl create namespace ci --dry-run=client -o yaml | kubectl apply -f -
kubectl -n ci create secret generic renovate-credentials --from-file=RENOVATE_TOKEN=/secure/renovate-token
```

The initial config targets `basarsubasi-gitops/kubernetes/flux`, disables account-wide
autodiscovery and onboarding, and uses `dryRun: full`. This performs extraction and
lookup without creating branches or merge requests. Review logs and repository
scope, then remove `dryRun` to enable writes. For normal operation, configure the
repository's Renovate policy and onboarding preference deliberately.

```sh
kustomize build flux/infrastructure/ci/renovate
helm repo add renovate https://docs.renovatebot.com/helm-charts
helm pull renovate/renovate --version 46.396.0 --untar --untardir /tmp/renovate-chart
helm lint /tmp/renovate-chart/renovate -f flux/infrastructure/ci/renovate/values.yaml
helm upgrade --install renovate renovate/renovate --version 46.396.0 \
  -n ci -f flux/infrastructure/ci/renovate/values.yaml --wait --timeout 5m
kubectl -n ci create job renovate-manual --from=cronjob/renovate
kubectl -n ci logs job/renovate-manual
```

For Flux, select its source/component in the consuming overlay, after credential
provisioning. CronJob creation does not prove authentication or extraction:
require a completed Job with authenticated repository processing and inspect
warnings/errors and extracted dependency counts. No write-mode or MR-creation
claim follows from a dry run. Remove temporary manual Jobs after verification.
