# Enable and verify Tetragon and Trivy Operator

No playground is running. These templates are locally validated only. The platform
selects both components for normal reconciliation, with readiness dependencies;
there is no resource-based enablement step. Resource availability is assumed.

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

## Reconcile and verify

The platform already selects both components. Shared HelmReleases reconcile when
included, and the parent Kustomizations are not suspended. No flags need changing.
After committing configuration changes, reconcile and verify normal readiness:

```sh
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization flux-system --timeout=2m
flux reconcile kustomization tetragon --timeout=15m
kubectl -n tetragon rollout status daemonset/tetragon --timeout=5m
kubectl -n tetragon rollout status deployment/tetragon-operator --timeout=5m
kubectl -n tetragon get servicemonitors
```

Verify a real process event using the [Tetragon guide](../../infrastructure/security/tetragon/README.md),
its VictoriaLogs record, and successful monitoring targets as part of acceptance.
No TracingPolicy is installed to kill or block processes.

Verify Trivy as well:

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
