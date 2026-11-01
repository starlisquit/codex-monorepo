# Flux Operator and Flux Web UI

The official Flux Operator chart `0.62.1` includes the Web UI. One deployment
provides both; a separate UI chart is not required. The included `FluxInstance`
installs and manages Flux `2.10.0` with source, Kustomize, Helm, and notification
controllers. Both versions were verified against stable upstream releases on
2026-11-01.

## Bootstrap a cluster without Flux

A HelmRelease cannot install anything until Flux's Helm controller is running.
These steps assume a working Kubernetes API, DNS, and pod network. If the cluster
has no CNI yet, seed networking before starting Flux. Install the operator once
with Helm, then let the FluxInstance create Flux:

```sh
helm upgrade --install flux-operator \
  oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
  --version 0.62.1 \
  --namespace flux-system --create-namespace \
  -f flux/infrastructure/gitops/flux-operator/values.yaml \
  --set serviceMonitor.create=false \
  --wait

kubectl apply -f flux/infrastructure/gitops/flux-operator/fluxinstance.yaml
kubectl -n flux-system wait fluxinstance/flux \
  --for=condition=Ready --timeout=5m
```

The bootstrap override temporarily skips the ServiceMonitor because its CRD is not
installed yet. The UI and operator are still enabled. No bootstrap commands were
executed against a cluster while preparing these templates.

Next, configure this repository as a Flux GitRepository, supplying a Kubernetes
Git authentication Secret if the repository requires it. Create cluster-specific
Flux Kustomizations in this order:

1. `./flux/infrastructure/sources`.
2. `./flux/infrastructure/observability/prometheus-operator-crds`; unsuspend its
   HelmRelease and wait for successful installation.
3. `./flux/infrastructure/gitops/flux-operator`; unsuspend its HelmRelease. It uses
   the same Helm release name and namespace as the seed install, enabling Flux to
   reconcile that release and restore its ServiceMonitor setting.
4. Add the other selected infrastructure components with their documented
   dependencies; create their namespaces before reconciliation.

The FluxInstance deliberately has no repository sync configuration: a cluster
reconciliation path has not been chosen. Installing it creates the controllers,
not a GitRepository or reconciliation of this entire infrastructure tree. Do not
point a sync at the infrastructure root, which has no aggregate Kustomization.
The raw FluxInstance is included in this component's Kustomize resources, while
the operator's HelmRelease remains suspended until deliberately enabled.

This is the bootstrap boundary, not a circular runtime dependency. Keep Helm,
the pinned operator chart reference, this configuration, cluster credentials, and
a recovery procedure available outside Flux so a broken controller can be repaired.
A reinstall or migration of an existing Flux installation needs a separate plan;
the steps above assume a new cluster.

## UI and monitoring

The UI is enabled on the internal Service, with ingress and HTTPRoute disabled.
For local administrative access after installation:

```sh
kubectl -n flux-system port-forward service/flux-operator 9080:9080
```

Configure the Web Config API's authentication and user access before exposing the
UI beyond local administrative access. The operator runs with its chart-defined
cluster administration permissions; avoid granting UI users unnecessary access.

Its ServiceMonitor is enabled in Git and collected through the VM operator's
Prometheus conversion and VMAgent discovery. The chart's NetworkPolicy permits
its web and metrics ports. The release depends on the monitoring CRD release.

References:

- [Installation](https://fluxoperator.dev/docs/installation/)
- [FluxInstance](https://fluxoperator.dev/docs/crd/fluxinstance/)
- [Web UI](https://fluxoperator.dev/web-ui/)
