# Deployment findings — 2026-11-01

This is a historical verification record for the
[`iximiuz-platform` play](https://labs.iximiuz.com/playgrounds/codex-platform-243e14fd/6ae6c40156e9b785c3220466).
The smaller original play was retained. No live API investigation is being
continued as part of this documentation update.

| Area | Evidence gathered | Remaining limit |
| --- | --- | --- |
| Cilium | Three agents Ready; kube-proxy replacement enabled; original cluster passed DNS, ClusterIP, and NodePort checks from every node | Full connectivity conformance suite not run |
| Rook/Ceph | Three monitors in quorum, three OSDs up/in, 33 active+clean PGs; RBD write/read Job passed | Ceph reports authentication compatibility warnings |
| Storage consumers | Observed PVCs Bound after CSI installation | No off-cluster backup or restore test |
| PostgreSQL | Three instances Ready; `Cluster in healthy state` | Failover and backup recovery not tested |
| NATS / Valkey | HelmReleases Ready; three NATS replicas running; Valkey running with RBD persistence | Application durability/failure tests not run |
| OpenBao | Three replicas initialized as one Raft cluster and unsealed; TLS Certificates Ready | Recovery material remains in an owner-only lab file; production key custody and auto-unseal not configured |
| External Secrets | Namespaced SecretStore Ready; verification ExternalSecret SecretSynced | Only the scoped `kv/data/lab/*` role configured |
| Observability | VictoriaMetrics, VictoriaLogs, VictoriaTraces and agents running; 71 of 74 observed scrape series up at one check | Three control-plane targets had TLS errors; full demo export not verified |
| Grafana | External Grafana binding complete; five datasource CRs synchronized; all 55 observed dashboard CRs synchronized | Cross-signal navigation not configured |
| Other charts | cert-manager, trust-manager, Kyverno, KEDA, Headlamp, Flux UI and blackbox release Ready at recorded checks | User login and policy/scaling behavior not comprehensively tested |
| Demo | Helm 4 null-pipeline render failure identified; explicit Collector config rendered; updated ConfigMap applied | Full workload readiness and metrics/logs/traces from real SDK traffic not established |
| API | Recovery after an etcd metrics edit succeeded; later API slowness observed | Slowness investigation explicitly paused; no final healthy API claim |

## Incidents and changes

1. The original cluster had no spare disks and too little capacity for this
   rollout, so a new play was created with explicit raw Ceph disks.
2. The kubeadm base installed kube-proxy despite selecting no CNI. The original
   cluster was migrated; the new manifest skips the kube-proxy addon entirely.
3. The standalone Flux UI crashed without FluxInstance API definitions. Installing
   those CRDs fixed discovery without enabling lifecycle controllers.
4. Trust-manager used its default `cert-manager` trust namespace; this repository
   installs cert-manager in `certificates`. The namespace and dependency were fixed.
5. Rook 1.21.1 needed a separate CSI driver chart in addition to its CSI operator.
   The driver chart was pinned to 1.1.0, matching the bundled CSI operator.
6. Helm 3 renders missed a Collector null-pipeline failure seen in the live Helm
   4 reconciliation. Explicit `alternateConfig` replaced deletion-by-null.
7. Editing etcd's metrics listener interrupted the API. Its original manifest
   was restored; temporary recovery using existing etcd data was removed once
   kubelet-managed etcd resumed. The API server and Cilium control-plane agent
   were restarted during recovery. Do not repeat that edit as a bootstrap step.
8. Further API slowness and asymmetric resource pressure were observed. Future
   playground sizing now prioritizes the control plane; the running VMs are unchanged.

The Git manifests express desired state. Consult [verification commands](../../runbooks/operations/verify-platform.md)
for current state and do not substitute this record for a live check.
