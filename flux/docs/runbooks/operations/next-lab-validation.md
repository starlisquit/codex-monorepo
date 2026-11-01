# Next iximiuz Labs validation handoff

Prepared 2026-11-01 after datasource template commit `71df400`. Validate the
current checkout, recording its actual SHA; later edits may change this list.
This is a work queue, not evidence that these checks passed. No playground is
running for the full platform. The last platform play was destroyed during an
unfinished PKI migration. Do not reuse historical readiness counts as acceptance.

## Scope and execution order

Use a **new** iximiuz Labs playground and the checked-in bootstrap procedures.
Do not modify or destroy the separate retained original small play. This handoff
does not provision anything. Assume sufficient resources: keep selected security
components and other infrastructure enabled rather than adding suspension gates.

1. Follow [provisioning](../bootstrap/01-provision-playground.md), using
   [the playground manifest](../bootstrap/iximiuz-playground.yaml). Confirm the
   control plane has more resources than each worker and the dev machine. Increase
   its allocation before creation if needed; the old sizing was not proven stable
   with the current full stack. Check kernel BTF/WireGuard support and raw Ceph
   disks before bootstrap.
2. Follow [Cilium and Flux](../bootstrap/02-cilium-and-flux.md), then
   [platform/storage gates](../bootstrap/03-platform-and-storage.md). Use a fresh
   cert-manager root; do not adopt a nonexistent CA from the destroyed play.
3. Follow [OpenBao initialization and ESO](../bootstrap/04-openbao-and-external-secrets.md).
   Keep recovery material outside Git and tool output. Let Flux follow its existing
   dependency graph; fix dependency problems in Git instead of bypassing gates.
4. Complete the checks below, starting with control-plane stability, networking,
   storage and PKI. Then exercise telemetry, policies, security, and backup/restore.
5. Commit fixes and a dated evidence report with remaining failures and limits.

Before deploying, from the repository root:

```sh
git rev-parse HEAD
flux/docs/runbooks/scripts/validate.sh
```

Use the Helm major version used by helm-controller when rendering changed charts.
Prior local validation included 91 Kustomize builds, dependency/storage checks,
chart renders for relevant changes, security-dashboard PromQL parsing, and the
PostgreSQL datasource's pinned CRD schema. None substitutes for live acceptance.

## 1. Fresh bootstrap and sustained controller health — highest priority

- [ ] Record playground ID, manifest, node CPU/RAM/disks, kernel and Kubernetes
  versions, repository SHA, and installed chart/image versions.
- [ ] Observe API and controller health throughout reconciliation and for at least
  30 minutes after convergence. Sample bounded `/readyz` requests, node usage,
  controller restarts/leader-election logs, events, and root-disk free space.
  The observation interval is a smoke test, not a capacity certification.
- [ ] All selected Flux Kustomizations and HelmReleases become Ready without
  manual suspension, repeated forced reconciles, or unrecorded live patches.
- [ ] Nodes remain Ready without pressure; workload PVCs bind and expected
  replicas run. Distinguish completed Jobs from failed workloads.
- [ ] If instability returns, capture CPU, memory, disk I/O and controller timing
  evidence before blaming demo load. Last-run control-plane load was extreme,
  but its single root cause was not established.

```sh
kubectl --request-timeout=10s get --raw=/readyz
flux check
flux get kustomizations -A
flux get helmreleases -A
kubectl get pods,pvc -A
kubectl top nodes
kubectl get events -A --sort-by=.lastTimestamp
```

Use [control-plane recovery](../recovery/control-plane.md) if needed. A successful
single health request does not establish sustained health.

## 2. Cilium and WireGuard — encryption never tested live

- [ ] Confirm bootstrap starts without kube-proxy, Cilium becomes healthy, and
  Flux takes ownership of the seed release without a networking outage.
- [ ] Run `cilium-dbg status --verbose` and `cilium-dbg encrypt status` in **each**
  Cilium agent. Confirm peers, kernel support, and node-to-node UDP 51871 access.
- [ ] Use disposable clients/servers pinned to different nodes. Verify Pod IP,
  ClusterIP and DNS connectivity; capture underlay packets during known traffic
  and correlate encrypted packets/counters with that traffic. Agent readiness or
  a WireGuard interface alone does not prove encryption.
- [ ] Check reconnect behavior after restarting one agent. Verify Hubble relay
  connections and central certificate trust separately.
- [ ] Record coverage accurately: same-node traffic and optional host/node
  encryption are outside the enabled setting; WireGuard uses Cilium keys, not
  our X.509 CA. SPIRE/workload mutual authentication is not enabled.

See [Cilium validation and limits](../../../infrastructure/networking/cilium/README.md).
Full Cilium conformance and L7/gRPC routing/metrics tests remain additional work;
only claim those if actually exercised with an appropriate proxy path/workload.

## 3. Storage and service continuity — regressions plus unresolved warnings

- [ ] Ceph has three OSDs up/in, monitor quorum, and a successful mounted RBD
  read/write smoke Job. Inspect `ceph health detail`; classify the previously
  observed authentication compatibility warnings instead of claiming HEALTH_OK.
- [ ] Exercise PVC persistence across a disposable consumer restart and CSI
  health. Record whether any controlled failure/recovery was tested.
- [ ] Verify three healthy CNPG instances, a SQL write/read and replication.
- [ ] Verify NATS messaging and route health, Valkey SET/GET persistence behavior,
  and three initialized/unsealed OpenBao replicas with functioning ESO sync.
- [ ] Test a controlled single-replica restart for replicated services after the
  basic checks pass. Do not equate replication with backup recoverability.

Follow [platform verification](verify-platform.md) and the component runbooks.

## 4. Central PKI — remaining acceptance

PKI scope updated 2026-11-02 (Europe/Istanbul); other sections retain their
original handoff scope. Use [current PKI procedures](pki.md) and the
[coverage inventory](../../architecture/pki-coverage.md). The
[interrupted full-platform run](../../findings/pki-last-run.md) remains historical.

Already verified in focused fresh runs: Hubble/node and explicitly enabled Relay
TLS/mTLS/flows, ClickHouse operator TLS/admission, and dedicated LiteLLM/SonarQube
PostgreSQL TLS/replication/application use. Those runs also verified changed served
serials/hot renewal; PostgreSQL primary failover passed. Real ESO and injected
agents subsequently authenticated to OpenBao with verified HTTPS. These results
do not establish a full-platform in-place CA migration.

- [ ] On the new selected deployment, confirm root/issuer readiness, actual
  validity/key identity, and public Bundle distribution before workload issuance.
  The current architecture signs leaves directly from the online root; there is
  no deployed intermediate/Vault issuer to assume ready.
- [ ] Complete a fresh stable Kyverno rollout, confirm disabled competing writers,
  settled leaf revisions and successful admission/cleanup webhooks.
- [ ] Complete NATS route/client TLS, quorum continuity, NATS Box trust, and Valkey
  plaintext rejection/probe/exporter verification, then test renewal/reload.
- [ ] Verify OpenBao/injector, ESO and other configured webhook serving chains,
  CA bundles, changed serials and clients after leaf renewal. Token renewal and
  application credential refresh do not substitute for TLS renewal acceptance.
- [ ] Complete Metrics Server serving/kubelet trust acceptance, VM Operator webhook
  renewal and Rook dashboard served-chain/reload checks for selected templates.
- [ ] Verify the generic application-db integration and any existing-cluster CA
  handover separately; preserve trust overlap and client reconnection behavior.
- [ ] Regress the previously verified Hubble/ClickHouse operator and dedicated
  PostgreSQL paths if versions/configuration change or they enter a broader
  deployment. Preserve the distinction between shared defaults and lab overrides.
- [ ] Inventory exceptions: Kubernetes PKI, cert-manager bootstrap webhook and
  CNPG operator webhook stay independent. Protect signing keys/issuers through
  RBAC; no certificate-policy template enforces central issuer selection.

## 5. Observability and dashboards — end-to-end regression

- [ ] Metrics API works via `kubectl top nodes` and `kubectl top pods -A`.
- [ ] All expected scrape targets are healthy or have a documented explanation.
  Revisit scheduler, controller-manager and etcd TLS/listener errors; retain
  verification rather than silencing errors with insecure settings.
- [ ] Generate quote traffic and prove recent metrics, SDK logs and a trace
  correlated by the same trace ID, following [platform verification](verify-platform.md).
- [ ] Verify node-local stdout/stderr ingestion from every node, Kubernetes
  metadata and severity normalization. Re-run the disposable severity Job and
  confirm TRACE, DEBUG, FATAL and unknown in queries and dashboard filters.
- [ ] Check log dashboard counts, severity/service rankings, recurring-message
  queries, namespace/Pod/container filters, single-line rows and expanded details
  through Grafana's actual datasource API and UI. Review frequent real errors;
  distinguish generated test messages from platform incidents.
- [ ] Confirm GrafanaDatasource/GrafanaDashboard synchronization and datasource
  UIDs. No plugin/query errors, broken variables, or misleading empty-as-zero panels.

See [container logging](container-logging.md). Stop forwards and remove temporary
traffic generators when finished; do not commit generated credentials.

## 6. Security tools and policies — first live validation for current templates

- [ ] Follow [security-tool verification](security-tools.md): Tetragon agents/BPF
  load on every intended node, harmless process exec produces an event, stdout
  export reaches VictoriaLogs, and ServiceMonitor series reach VictoriaMetrics.
- [ ] Trivy completes scans of actual workload images and creates fresh reports;
  check image identity, scan DB freshness, failed Jobs and registry access. A Ready
  operator is not evidence of successful scans or absence of vulnerabilities.
- [ ] Exercise both [security dashboards](../../../dashboards/security/README.md)
  with real reports/events. Validate filters and ranking/count semantics against
  report CRs and backend queries. Check export/drop/cache panels with available
  series; missing counters must not imply zero errors.
- [ ] Re-run `flux/docs/runbooks/scripts/test-network-policies.sh` after reviewing its
  scope. The historical 15 assertions predated later egress changes. Explicitly
  test default-deny **ingress and egress**, selected allowlist destinations/ports,
  DNS, forbidden destinations/ports and selector boundaries. NetworkPolicy allows
  are additive; test policy combinations, not just isolated manifests.
- [ ] Exercise Kyverno registry policy with allowed/disallowed fully qualified
  images, regular/init/ephemeral containers, and controller-generated Pods in
  scoped namespaces. Verify out-of-scope behavior and actual autogeneration.
  Use admission dry runs where possible; do not pull untrusted images to test denial.
- [ ] Verify other existing Kyverno Audit policies produce expected results and
  do not unexpectedly block platform bootstrap. There is no certificate policy.

## 7. PostgreSQL Grafana datasource — optional template acceptance

This example is intentionally unselected until configured. Follow
[its guide](../../../dashboards/datasources/README.md).

- [ ] Provision a dedicated read-only role, same-namespace credential Secret and
  public CA ConfigMap; select the example in its Kustomization.
- [ ] Confirm operator substitution, `verify-full` hostname validation and a
  successful Grafana query. Test wrong CA/hostname/credentials and denied writes
  using a disposable dataset. Verify connection-pool settings and network allows.
- [ ] Ensure no credentials enter Git/reports, existing default datasources keep
  their ownership, and this datasource's UID works in a dashboard.

## 8. Velero and recovery — backend configuration required

- [ ] Verify normal Helm rollout, plugin compatibility and monitoring. The base
  release alone has no functional backup destination or PVC data protection.
- [ ] With an available external test bucket and scoped credentials, follow
  [Velero](velero.md): storage location Available, metadata backup Completed,
  actual bucket objects, isolated namespace restore and recovered behavior.
- [ ] Record clearly that metadata smoke backup excludes PVC data. Ceph volume
  recovery, CNPG/OpenBao application-consistent restore, CA/unseal key custody,
  and recovery after original storage loss need separate tested procedures.
  If backend access is unavailable, mark restore checks Blocked, not Passed.

## Evidence and completion

Create a dated report under `flux/docs/findings/` with one row per check:
**Passed / Failed / Blocked / Not run**, timestamp, SHA, play ID, exact command or
query, sanitized result, and unresolved follow-up. Keep status distinct from
historical evidence. Record any manual fixes, put durable configuration changes
in Git, re-run affected checks, and update runbooks when commands differ in practice.

Preserve credentials, private keys and recovery material outside Git. Remove
disposable test workloads/forwards and restore any temporarily selected examples.
Record playground retention/teardown status; do not destroy a user's running lab
merely because validation finished. Completion requires explaining remaining gaps,
not turning every row green by weakening checks or disabling components.
