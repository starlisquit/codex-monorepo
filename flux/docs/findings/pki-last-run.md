# Last platform run and PKI migration — 2026-11-01

Play `6ae6cfaf789ac234e32e00bf` of playground `codex-platform-243e14fd`
was permanently destroyed at the user's request. No replacement was started.
Its Grafana forwards, temporary test Pods, disks and in-VM recovery files are no
longer available. This operation did not export CA private keys or OpenBao recovery
material. The separate original small play was not targeted.

This record supersedes any interpretation of earlier readiness snapshots as the
final state. **The PKI migration was unfinished when the play was destroyed.**
The manifests represent desired configuration, not a fully verified deployment.

## What worked earlier in this play

- The runbook bootstrap reached 29/29 Kustomizations and 22/22 HelmReleases Ready
  before subsequent additions and PKI changes. Ceph's mounted RBD smoke test passed,
  PostgreSQL had three healthy instances, and External Secrets synchronized from
  OpenBao. Ceph authentication compatibility warnings remained.
- The minimal quote application produced real SDK metrics, logs and traces in the
  three telemetry backends. Later, node-local vlagent collection returned container
  logs with Kubernetes namespace/Pod/container/node metadata from all three nodes.
- The Grafana log dashboard's filtered queries returned data through Grafana's
  actual datasource API. Unknown severity handling and TRACE/DEBUG/FATAL simulation
  were tested. The viewer was made single-line with inline labels hidden and
  expandable structured details retained.
- The isolated NetworkPolicy test passed 15 access assertions and outgoing DNS.
  These were real Pod-to-Pod tests of namespace AND Pod selectors, ports, and the
  optional namespace ingress baseline; test namespaces were removed.

See the more detailed historical [rebuild](rebuild-verification.md),
[error review](log-error-review.md), and
[NetworkPolicy test](../../policies/network/README.md) records.

## Central PKI: evidence and unfinished work

| Area | Evidence from this run | Limit at teardown |
| --- | --- | --- |
| Root/issuer | Existing OpenBao CA adopted into `certificates/platform-root-ca`; ClusterIssuer `platform-workload-ca` Ready | Private material existed only in this temporary cluster; no export performed during teardown |
| Root continuity | Public-key SHA-256 matched the previous OpenBao CA; the pre-migration OpenBao server certificate verified against the adopted root | This proves signing-identity continuity, not every client's live trust/reload behavior |
| Root lifetime | An explicit renewal with the existing key extended the root certificate to 2036-10-29 | Adopting an existing Secret alone did not immediately reissue it with the declared ten-year duration |
| Trust distribution | Bundle `platform-ca` reported Synced=True; its manifest targets public ConfigMaps across namespaces | Distribution does not mount trust into applications or configure their TLS clients |
| trust-manager / Metrics Server / OpenBao | Certificates Ready; corresponding staged Helm reconciliations succeeded | No final endpoint-by-endpoint handshake, renewed-serial, or client-authentication acceptance suite completed |
| PostgreSQL | Central server and replication Certificates Ready; three database instances were healthy at checks | Cluster reference update failed when CNPG's webhook refused connections; the desired external-certificate configuration was not verified live |
| NATS / Valkey | Both central Certificate resources Ready in the final snapshot; pinned chart renders supported the selected TLS settings | TLS workload rollout, NATS cluster continuity, client verification, plaintext rejection and exporter checks were not completed |
| Kyverno | Intermediate CA Certificates Ready; chart templates included `--disableCertManagerController=true` | Both leaf Certificates were **Ready=False** at the final snapshot; a stable issuer handover was not achieved |
| Hubble / VM Operator | Chart-native cert-manager settings rendered successfully | Final live certificate-chain and connection verification was not completed |
| PKI policy | `platform-pki-issuers` exists as an Audit/Ignore template | It is **excluded** from `policies/kyverno/kustomization.yaml`, so normal Flux reconciliation does not install it; it was not an enforcement guarantee; the template was subsequently removed |

The final certificate listing contained 14 resources: 12 Ready and two unready
Kyverno leaves. A legacy OpenBao CA Certificate was present again in that listing.
The repository was reverted and then reapplied during the interrupted migration;
that temporary state must not be mistaken for a clean completed issuer inventory.

## Failure modes and lessons

Kyverno showed repeated `SecretMismatch` issuance with a rapidly increasing
Certificate revision: the private key in the serving Secret did not match the
current CertificateRequest. Deployment templates contained the flag disabling
Kyverno's own certificate controller, while still-running old Pods lacked that
flag. This is evidence consistent with competing certificate writers during a
stalled rollout. A transient Ready condition did not establish a stable handover.
The old admission/cleanup controllers were temporarily scaled down and their old
Pods removed; scale-back-to-one requests succeeded, but final readiness was not
established before destruction. Do not repeat this as an unattended production
migration procedure.

The control-plane controller-manager repeatedly lost leadership and entered
CrashLoopBackOff. Deployment status lagged the new template, so a successful API
patch did not mean new Pods were running. Restarting kubelet on the control plane
cleared restart backoff; a later snapshot showed controller-manager Ready again.
No kubeadm certificate or static-pod manifest was changed. This was a recovery
attempt, not proof of durable API stability.

The control plane reached load averages around 73 while a worker snapshot was
around 1.1. API timeouts, unavailable CNPG webhooks, and controller restarts
interrupted the rollout. Readiness sometimes returned `ok` between these failures.
The stalls predated PKI migration. These samples do not isolate CPU, memory,
root-disk I/O, certificate churn or the underlying host as the single cause.
Investigate the control plane before another broad rollout.

## Next-run acceptance criteria

1. Establish sustained control-plane/controller health before changing issuers.
2. On a **fresh** playground, skip CA adoption and let cert-manager create the root.
   On an existing cluster, back up signing material and plan trust overlap before
   switching issuers. Protect keys outside Git.
3. Confirm the root's actual validity and key continuity. If adopting a preexisting
   Secret, use an explicit renewal when needed; do not assume requested duration
   alone immediately changes its existing certificate.
4. Complete issuer, trust-manager, and Bundle gates before application migrations.
5. For existing Kyverno, ensure the old certificate writer is stopped and new Pods
   really run with certificate management disabled before cert-manager owns the
   same Secrets. Check that revisions settle and webhooks still accept requests.
6. Test each migrated service with a verified connection and the intended hostname,
   then test wrong-CA rejection and any promised plaintext/mTLS rejection. Confirm
   replication, probes, metrics exporters and post-renewal reloads separately.
7. Protect issuer/key access through RBAC and verify actual TLS behavior. The
   certificate-policy template was subsequently removed; issuer references alone
   never proved that an application loaded or used its certificate.

Central issuance does not imply all internal HTTP was converted to HTTPS. The
selected design still allows internal HTTP; Kubernetes PKI and CNPG operator's
own bootstrap webhook PKI remain explicit independently managed exceptions.
