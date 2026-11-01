# Enable and verify Tetragon and Trivy Operator

No playground is running. The security templates are locally validated only. Fix
control-plane reliability and reserve the additional memory/CPU/disk capacity
listed in [security sizing](../../infrastructure/security/README.md) before enabling them.

## Preflight

From each node's terminal, verify a readable `/sys/kernel/btf/vmlinux`, kernel
version (`uname -r`), and available memory/disk. Verify the chosen Tetragon image
supports that kernel and required BPF features. Operator/scan workers must exist
without control-plane/master labels; otherwise affinity will leave Pods Pending.

From the dev machine:

```sh
kubectl get nodes -L node-role.kubernetes.io/control-plane,node-role.kubernetes.io/master
kubectl get --raw=/readyz
flux get kustomizations -A
kubectl get crd servicemonitors.monitoring.coreos.com
kubectl get pods -A
kubectl top nodes
kustomize build flux/clusters/iximiuz-platform/tetragon
kustomize build flux/clusters/iximiuz-platform/trivy-operator
```

A healthy `/readyz` snapshot alone did not rule out intermittent stalls in the last
run. Check sustained controller stability. On a node, also inspect `df -h /`;
Ceph capacity does not protect root disks from image-layer/scan-file exhaustion.

## Enable through Git, one component at a time

In `flux/clusters/iximiuz-platform/infrastructure.yaml`, set **only** the chosen
`tetragon` or `trivy-operator` Kustomization's `spec.suspend` to `false`. Commit and
push, then reconcile the source/root and that component after dependencies become
Ready. The cluster overlays already set the child HelmRelease suspend flag false;
shared security releases stay suspended for other clusters.

```sh
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization flux-system --timeout=2m
flux reconcile kustomization tetragon --timeout=15m
kubectl -n tetragon rollout status daemonset/tetragon --timeout=5m
kubectl -n tetragon rollout status deployment/tetragon-operator --timeout=5m
kubectl -n tetragon get servicemonitors
```

Verify a real process event using the [Tetragon guide](../../infrastructure/security/tetragon/README.md),
its VictoriaLogs record, and successful monitoring targets before proceeding.
No TracingPolicy is installed to kill or block processes.

After committing the Trivy Kustomization enablement separately:

```sh
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization flux-system --timeout=2m
flux reconcile kustomization trivy-operator --timeout=15m
kubectl -n trivy-system rollout status deployment/trivy-operator --timeout=5m
kubectl -n trivy-system get jobs,pods
kubectl get vulnerabilityreports,configauditreports -A
```

Inspect scan Job completion and a report tied to the actual demo image. A Ready
HelmRelease does not prove successful scans or clean findings. Query the existing
vmagent target API and confirm both ServiceMonitors are scraped; CRDs and chart
renders alone do not prove metrics ingestion. Review root-disk/memory use before
expanding target namespaces or enabling further scanners.

## Pause or remove

Suspending a Flux Kustomization or HelmRelease **does not stop existing agents,
operators or scan Jobs**. It only stops reconciliation. To stop running components,
make an explicit Git removal/disablement and review Helm/CRD retention behavior;
coordinate deleting active scan Jobs and retaining reports as appropriate. Restore
Git settings after any temporary manual scaling so Flux does not undo it.
