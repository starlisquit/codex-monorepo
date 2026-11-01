# 3. Follow platform and storage readiness

Flux creates the dependency graph automatically. Read it in
[architecture](../../docs/architecture/deployment-order.md). Do not manually
unsuspend every shared HelmRelease or bypass storage gates to clear Pending Pods.

From `dev-machine`:

```sh
flux get kustomizations -A
flux get helmreleases -A
kubectl get pods -A
```

For an intentional manual refresh, follow the foundations first:

```sh
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization foundation --timeout=3m
flux reconcile kustomization monitoring-crds --timeout=3m
flux reconcile kustomization rook-operator --timeout=5m
flux reconcile kustomization csi-drivers --timeout=5m
flux reconcile kustomization ceph --timeout=15m
flux reconcile kustomization storage-ready --timeout=5m
```

The storage driver chart is separate from the Rook/CSI operator chart. Confirm
both layers and actual I/O:

```sh
kubectl get csidrivers
kubectl -n rook-ceph get drivers.csi.ceph.io
kubectl -n rook-ceph get cephcluster,cephblockpool
kubectl -n rook-ceph exec deploy/rook-ceph-tools -- ceph status
kubectl -n rook-ceph exec deploy/rook-ceph-tools -- ceph health detail
kubectl -n rook-ceph wait --for=condition=Complete job/ceph-storage-check --timeout=5m
kubectl -n rook-ceph logs job/ceph-storage-check
kubectl get pvc -A
```

Expect the RBD driver `rook-ceph.rbd.csi.ceph.com`, three monitors in quorum,
three OSDs up/in, a ready block pool, test output `PASS`, and Bound PVCs. Ceph
may report the documented lab authentication warnings. Diagnose other warnings
rather than treating the HEALTH_WARN gate as blanket approval.

To rerun **only** the storage test, keep its PVC and remove the completed Job:

```sh
kubectl -n rook-ceph delete job ceph-storage-check
flux reconcile kustomization storage-ready --timeout=5m
kubectl -n rook-ceph logs job/ceph-storage-check
```

Never delete the CephCluster, database, real workload PVCs, or raw disk contents
as a generic bootstrap retry. The test PVC and Job names are deliberately separate.

PostgreSQL, NATS, Valkey, OpenBao, and observability follow storage readiness.
OpenBao will remain unready until initialized and unsealed; that is an expected
manual gate. Continue with [OpenBao](04-openbao-and-external-secrets.md).
