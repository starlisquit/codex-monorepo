# Fresh platform rebuild — 2026-11-01

This is historical evidence from the initial successful bootstrap. The play was
later destroyed after an unfinished PKI migration; see the
[last-run report](pki-last-run.md) for its final state.

The previous full-platform play `6ae6c40156e9b785c3220466` was destroyed at the
user's request. This was a fresh bootstrap, with no application data migration.
The separate original small `iximiuz-labs` play was retained.

[New play](https://labs.iximiuz.com/playgrounds/codex-platform-243e14fd/6ae6cfaf789ac234e32e00bf)
uses the committed playground manifest and bootstrap runbooks: control plane
4 CPU / 6 GiB, two workers each 2 CPU / 4608 MiB, and a separate dev machine
1 CPU / 1 GiB. Each Kubernetes node has a 20 GiB root disk and dedicated raw
25 GiB `/dev/vdb` for Ceph. LVM and the RBD kernel module were prepared by the
playground startup tasks. kubeadm skipped kube-proxy entirely.

## Procedure exercised

The checked-in `bootstrap-cilium.sh` and `bootstrap-flux.sh` installed networking
and Flux for `flux/clusters/iximiuz-platform` at revision `858ed25`. Flux followed
the dependency graph through CRDs, operators, Ceph, the RBD smoke test, storage
consumers, observability, and the reduced demo. Cilium's initial seed installation
was subsequently reconciled by its Flux HelmRelease.

Both checked-in OpenBao Python helpers ran successfully. The first initialized
the Raft cluster once and unsealed all three replicas; the second configured the
scoped lab Kubernetes auth role and verification value. At that check, recovery material was retained
in `/home/laborant/.config/codex-platform/openbao-init.json` with mode `0600`;
its contents were neither printed nor committed. Retain it independently before
discarding this playground.

## Live checks

| Area | Observed result |
| --- | --- |
| Flux | `flux check` passed; all 28 child Kustomizations plus the root (29 total) and 22 HelmReleases Ready |
| Nodes | Three Ready; MemoryPressure, DiskPressure, PIDPressure False |
| Networking | Cilium agents and Envoy Ready; no kube-proxy DaemonSet |
| Storage | Three Ceph OSDs up/in, monitor quorum formed; mounted RBD read/write Job PASS; all 16 observed PVCs Bound |
| PostgreSQL | Three instances Ready; Cluster in healthy state |
| OpenBao / ESO | Three replicas unsealed and Ready; SecretStore Valid; verification ExternalSecret SecretSynced |
| Metrics API | APIService Available; `kubectl top nodes` and demo pod metrics work |
| Grafana | Binding complete/success; five datasource CRs and 55 dashboard CRs provisioned |
| Demo | Exactly currency, quote, and otel-collector Deployments, each 1/1, all on workers |
| Quote traffic | Four POST requests with numberOfItems=2 returned 17.98 |
| Metrics signal | VictoriaMetrics range query returned `quotes` samples increasing from 1 to 4 with `service.name=quote` |
| Logs signal | VictoriaLogs returned actual SDK `Calculated quote` records and total 17.98 |
| Traces signal | VictoriaTraces returned the log's exact trace ID, with POST /getquote and calculate-quote spans |

The matching log/trace ID was `23551c1f3df60b6ef3e7796adcee091f`. It is evidence
from this bounded check, not a permanent query target after the two-day retention.
Use a fresh request and its log trace ID for subsequent checks. OTLP resource
labels retain dotted names (`service.name`); do not assume `service_name`.
Metrics ingestion/query visibility can lag; a recent range query established
samples even while an immediately repeated instant query was empty.

At one post-bootstrap snapshot, node memory was approximately 4596 MiB (77%)
on the control plane, 3117 MiB (70%) and 2644 MiB (60%) on workers. CPU was
7–13%. The demo consumed approximately 54 MiB total across its three Pods.
These are short snapshots, not a sustained capacity or performance test.

## Runbook correction and remaining limits

OpenBao's StatefulSet uses `OnDelete`; `kubectl rollout status` rejects that
strategy. Bootstrap and recovery procedures now wait for three ready replicas.
Its Flux health expression also explicitly requires all desired replicas Ready.

Ceph reports the documented AES authentication compatibility warnings, not
HEALTH_OK. VictoriaMetrics observed 73 of 76 scrape series up; controller-manager,
scheduler, and etcd still have the documented certificate/listener limitations.
No static control-plane manifests or etcd listeners were changed during this
rebuild. No failover, backup restore, full Cilium conformance, or sustained load
test was performed.
