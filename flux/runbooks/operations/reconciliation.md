# Reconciliation and failed releases

From `dev-machine`, first read the failing resource and its dependency:

```sh
flux get kustomizations -A
flux get helmreleases -A
kubectl -n flux-system describe kustomization storage-ready
kubectl -n rook-ceph describe helmrelease ceph-csi-drivers
kubectl get events -A --field-selector=type=Warning --sort-by=.lastTimestamp
```

Substitute the actual names shown by Flux. Look at conditions, observed generation,
source revision, and whether an operation is still in progress. A pending PVC
before CSI readiness has a different cause from insufficient memory or an
untrusted serving certificate.

## Apply a corrected Git change

Commit and push first; Flux follows `main`, not your local worktree. Render the
changed Kustomization and chart with the runtime's Helm major version before
pushing. Then:

```sh
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization flux-system --timeout=3m
flux reconcile kustomization foundation --timeout=3m
flux reconcile kustomization monitoring-crds --timeout=3m
```

Follow the specific downstream dependency chain, for example Rook → CSI/Ceph →
storage-ready → consumer. Do not annotate every object repeatedly during a slow
API incident. Long health checks may still evaluate an older revision until
completion; one annotation does not necessarily cancel their in-flight wait.

Once prerequisites and the committed fix are present, reset a failed Helm action
using Flux rather than manual `helm upgrade`:

```sh
flux reconcile helmrelease opentelemetry-demo -n demo --reset --timeout=15m
```

If working through a tool with a short command timeout, detach the whole job:

```sh
nohup bash -c 'flux reconcile helmrelease opentelemetry-demo -n demo --reset --timeout=15m' \
  > /tmp/demo-reconcile.log 2>&1 < /dev/null &
tail -n 50 /tmp/demo-reconcile.log
```

## Interrupted Helm operations

```sh
helm status victoria-metrics-k8s-stack -n observability
kubectl -n observability describe helmrelease victoria-metrics-k8s-stack
kubectl -n flux-system logs deployment/helm-controller --since=10m
```

After the recorded API interruption, helm-controller unlocked a pending install
and performed an upgrade. Let it recover after prerequisites are healthy; do not
blindly delete Helm release Secrets or install a second release. If a controller
restart becomes necessary to recover a proven stuck watch, do it once during an
appropriate maintenance window, then verify source and application reconciliation.
The current API slowness investigation is paused, so no such restart is prescribed
as part of the documentation changes.
