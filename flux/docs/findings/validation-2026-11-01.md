# Focused verification and interrupted full-platform run — 2026-11-01

## Full-platform run, 11:38–11:55 Europe/Istanbul (08:38–08:55 UTC)

Play `6ae6fa7756e9b785c3292646`, playground `codex-platform-243e14fd`, was
destroyed immediately at the user's request when the validation strategy changed.
Its ephemeral data and OpenBao recovery material were not exported. No retained
original playground was modified. Initial checkout: `1bf8c0d`; deployed seed:
`f547416`; source later fetched `a885881`, but final application of every fix
was not established. This report is not a full acceptance sign-off.

| Check / command | Status | Sanitized evidence and limits |
| --- | --- | --- |
| `flux/runbooks/scripts/validate.sh` | Passed | 91 Kustomize builds, 37 child dependency definitions, 25 release coverage checks at this revision |
| Node preflight: `free -m`, `nproc`, `lsblk`, BTF, `modprobe wireguard/rbd`, LVM | Passed | Control plane 4 CPU/6004 MiB; workers 2 CPU/4492 MiB each; Linux 6.1.167; 20 GiB system disks and unused 25 GiB raw Ceph disks; Kubernetes v1.37.1 node reports |
| Fresh Cilium seed | Passed after fix | Original seed failed on absent Certificate CRDs. Deferring Hubble, relay/UI and central CA bundle allowed networking before PKI; WireGuard retained |
| Flux seed adoption | Passed | Cilium 1.20.4 release revision 2 Ready; no kube-proxy; three nodes Ready |
| Cross-node Pod IP, ClusterIP and DNS | Passed | Disposable clients on node-01 and server on node-02; 50 HTTP requests succeeded |
| WireGuard evidence | Passed, bounded | Every agent reported two peers; underlay capture during known traffic contained 879 UDP/51871 packets and zero plaintext Pod TCP/8080 packets; peer transfer counters increased. This is not full conformance or host encryption coverage |
| Hubble TLS | Passed, bounded | Relay logged TLS connections to all three peers; presented leaf verified against central root; wrong CA and hostname rejected |
| Agent restart/reconnect | Not run | No controlled Cilium restart completed |
| NetworkPolicy integration script | Passed | Existing script exited 0; ingress selector/namespace/port boundaries and additive ingress/egress behavior tested; temporary namespaces removed |
| Additional egress/allowlist tests | Passed | Selected destination/port allowed; wrong port, label and namespace denied; DNS explicitly allowed; unselected client unaffected until namespace baseline; baseline denied unallowed egress and DNS; additive allow survived |
| Ceph quorum/OSDs/RBD smoke | Passed with warnings | Three OSDs, Cluster Ready, mounted read/write Job output PASS. Health warnings: insecure AES CSI key types and monitor compatibility allowances; not HEALTH_OK |
| PVC persistence after cross-node consumer replacement | Not run to completion | Marker written, first consumer deleted and replacement created; final read was not observed before teardown |
| Central root and public trust distribution | Passed, bounded | Fresh self-signed root valid through 2036-10-29; Bundle platform-ca Synced. This does not prove every consumer trusts it |
| Metrics Server/trust-manager/ESO live TLS | Passed | Verified expected service hostnames and root CA; wrong CA and hostname rejected |
| Kyverno certificate readiness | Failed | Both leaf Certificates Ready, but admission readiness HTTP 500. Leaf Secret contained two certificates. Pinned v1.19.2 decodeTLSSecret rejects chains longer than one certificate; external TLS chain itself verified |
| Kyverno durable fix | Not run live | `a885881` replaces delegated leaf issuance with direct central-root leaves and a public-only CA Secret from trust-manager; Helm 3 and Helm 4.3.1 render/post-render checks passed. Final controller rollout not observed |
| Trivy operator resource configuration | Failed before fix | Repeated OOMKilled at 256 MiB; scan Jobs reported insufficient memory/ephemeral storage. Some real reports were produced, so neither total failure nor complete coverage is claimed |
| Trivy durable resource fix | Not run live | `505d3c4` raises operator limit to 1 GiB and adjusts reservations/concurrency. Last observed Deployment still used old values; do not claim the fix resolved runtime health |
| Tetragon | Passed startup only | Three agents 2/2 and operator Ready; no end-to-end event or dashboard validation completed |
| PostgreSQL | Not run to completion | Primary and first replica Ready, WAL streaming logged, third replica provisioning. SQL/replication acceptance command timed out during API instability |
| OpenBao/ESO | Not run to completion | First two replicas initialized/unsealed with checked-in helper; third was Pending at last snapshot. No completed ESO marker acceptance |
| NATS/Valkey service continuity and TLS | Not run | Issued leaves Ready; workload acceptance not completed |
| Other PKI handshakes and renewal/reload | Not run | Missing endpoints in early checks were bootstrap timing, not established final failures |
| Metrics API | Passed, bounded | kubectl top nodes returned samples; this does not establish all scrape targets healthy |
| Grafana/telemetry/security dashboard regression | Not run | Grafana still initializing; SDK metrics/log/trace correlation and actual dashboard queries not completed |
| Registry admission policy | Not run | Test helper prepared but policy had not yet reconciled |
| Optional PostgreSQL datasource | Not run | Example remained unselected; no credentials provisioned |
| Velero normal Helm rollout | Passed | HelmRelease Ready for chart 12.2.2; no backend configured |
| Backup/restore | Blocked | User confirmed no external bucket; no metadata or PVC recovery claim |
| Sustained API/controller health | Failed | At 08:54 UTC bounded readyz failed etcd/etcd-readiness. Control plane used 5404/6004 MiB, load 20.17; vmstat showed 83–88% I/O wait and substantial reads. These samples support investigating storage/reclaim contention, not a uniquely proven cause. No 30-minute post-convergence interval achieved |
| Full convergence | Failed | Selected components had not all become healthy before teardown; no suspension or weakened TLS was used to claim success |

The new user instruction is to validate small component sets in independent
playgrounds, publish evidence and fixes to both remotes, then destroy unused plays.
