# Full iximiuz Labs platform

This cluster overlay enables every infrastructure HelmRelease and the PostgreSQL
instance, dashboards, and datasource configuration. The demo template deliberately
selects only currency and quote, plus the Collector; it is not the full storefront. Shared templates remain
suspended for other clusters; this overlay enables each selected release.

## Playground

- Playground: `codex-platform-243e14fd` (base: `k8s-omni`).
- Play: <https://labs.iximiuz.com/playgrounds/codex-platform-243e14fd/6ae6cfaf789ac234e32e00bf>.
- `cplane-01`: 4 vCPUs and 6 GiB requested RAM.
- `node-01` and `node-02`: 2 vCPUs and 4608 MiB requested RAM each.
- Every Kubernetes node has a 20 GiB system disk and raw 25 GiB `/dev/vdb`.
- `dev-machine`: 1 vCPU, 1 GiB RAM, 10 GiB system disk.
- kubeadm skips `addon/kube-proxy`; Cilium uses the direct API endpoint
  `172.16.0.2:6443`, Kubernetes IPAM, and kube-proxy replacement.
- LVM tools are installed and the RBD kernel module is loaded on every node.

The original `iximiuz-labs` play is retained separately. It does not reconcile
this overlay. No workloads or stored application data were migrated from it.

## Deployment order

`infrastructure.yaml` defines the Flux dependency graph and health checks:

1. Foundation namespaces and chart sources.
2. Prometheus monitoring CRDs and Gateway API v1.4.0 standard CRDs.
3. Full Cilium monitoring/Gateway integration, Rook/CSI operator, the separate
   CSI driver chart, Grafana Operator,
   CloudNativePG operator, cert-manager, and independent infrastructure services.
4. Rook Ceph cluster, with one explicitly selected raw `/dev/vdb` on each node.
5. A mounted RBD PVC write/read check, then the VictoriaMetrics stack after
   storage and Grafana Operator; PostgreSQL, NATS,
   Valkey, and OpenBao after their storage and operator/certificate prerequisites.
6. VictoriaTraces agent, blackbox probing, and Grafana dashboards after the stack.
7. OpenTelemetry demo after the observability stack and traces agent.

Metrics Server independently follows cert-manager and monitoring CRDs. Its
APIService readiness gates `kubectl top` and CPU/memory Metrics API availability;
it does not depend on Ceph or VictoriaMetrics. See its
[component guide](../../infrastructure/observability/metrics-server/README.md).

Trust-manager waits for cert-manager. Every monitoring-enabled release waits
for the monitoring CRDs. A release's dependencies are readiness gates, not just
apply ordering. Cilium is initially installed with minimal Helm values before
Flux so the controllers have networking; Flux then reconciles the full settings.

Ceph and PostgreSQL Kustomizations use `prune: false`; deleting their paths from
Git does not automatically delete storage or the database. This is not a backup.
The OpenBao and Gateway API Kustomizations also disable pruning.

## Lab sizing

The three OSDs provide 75 GiB raw capacity, about 25 GiB before overhead with
three-way replication. Only RBD block storage is enabled; CephFS and RGW are
omitted. The RBD pool retains three host-separated replicas. Ceph OSD, monitor,
and manager resource settings are reduced for this lab.

Cluster overrides request 1 GiB per PostgreSQL instance, NATS JetStream replica,
and OpenBao replica. Valkey has a 1 GiB RBD volume. VictoriaMetrics, VictoriaLogs,
and VictoriaTraces request 2 GiB each, Grafana 1 GiB, and Alertmanager 1 GiB.
Telemetry retention is two days. These sizes are for demonstration and do not
represent production retention, capacity, or availability planning.

All web applications use internal Services. Headlamp retains user-authenticated
RBAC; its service account is not granted cluster-admin. No public exposure or
plaintext credentials are committed.

## Documentation and reproducible bootstrap

- [Architecture, findings, and unresolved issues](../../docs/README.md)
- [Exact bootstrap and recovery procedures](../../runbooks/README.md)
- [Future playground sizing](../../docs/architecture/playground-sizing.md)

The prior full-platform play was destroyed at the user's request and rebuilt
from the runbooks using the revised sizing and minimal demo. Historical resource
pressure findings refer to that previous play. Demo services stay on workers and
Kustomize controller concurrency is capped at four to reduce API bursts.

## Operations

Use the playground's `dev-machine` terminal:

```sh
flux get all -A
kubectl get pods -A
kubectl get pvc -A
kubectl -n rook-ceph get cephcluster
kubectl -n rook-ceph exec deploy/rook-ceph-tools -- ceph status
kubectl -n databases get cluster application-db
```

OpenBao was initialized once and all three replicas were unsealed in the recorded
play. External Secrets synchronized a scoped verification value through its
Git-managed SecretStore. A fresh play still requires the operational initialization
and auth configuration from the runbooks; those steps are not supplied by the
Helm chart. Keep all recovery material outside Git and independently retained.

For a fresh play, install Cilium first, bootstrap the committed Flux manifests
under this directory, and let Flux follow the readiness graph. This playground
has temporary disks unless persisted through iximiuz Labs; replication is not
an off-cluster backup.
