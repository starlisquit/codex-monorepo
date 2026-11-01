# Deployment External Secrets: K3s runtime verification

**Passed.** Playground `6ae7a3507f32053bde2bc71a`, created concurrently with the
injector playground. Flux reconciled only
`flux/clusters/20261101-233840-deployment-eso-2bc71a` at tested configuration
`4bfce4a958eb154128833151e3279acc54d76e2c`. Evidence captured at **23:48:18
Europe/Istanbul**, 2026-11-01 (20:48:18 UTC).

Versions: K3s `v1.37.1+k3s1`, Flux `2.10.0`, cert-manager `v1.21.3`,
trust-manager `v0.26.0`, official OpenBao chart `0.30.6` / OpenBao `2.7.2`,
and official External Secrets chart `2.14.0`. Only ESO, PKI/trust, one OpenBao
Raft replica and two application fixtures were deployed; no injector or
monitoring stack was needed on this cluster.

## Actual runtime results

- Both application-specific ServiceAccounts, SecretStores and ExternalSecrets
  reconciled under namespace/name-prefix transforms. ESO authenticated through
  Kubernetes service-account JWTs with audience `openbao`, read the assigned KV
  paths over verified HTTPS and created the two distinct target Secrets.
- The non-root applications actually consumed `APP_PASSWORD` through `envFrom`;
  HTTP probes returned SHA-256 fingerprints matching their randomized provider
  values. Applications did not receive OpenBao administrative tokens or mounted
  API service-account credentials.
- Generated target Secrets had ExternalSecret owner references. Neither PKI nor
  CNPG/other controller-managed Secrets were adopted or overwritten.
- Own-path reads succeeded. Cross-application reads, wrong service account,
  same-named account in the wrong namespace and wrong audience all returned
  **HTTP403**. Explicit self-token lookup and renewal permissions worked.
- Updating only API's KV value changed its Kubernetes Secret. The existing app
  process retained its old environment value, as expected. After a Deployment
  rollout the replacement Pod read the new value; worker's original Pod UID and
  credential fingerprint remained unchanged.
- Soft-deleting API's provider value caused its ExternalSecret to lose readiness.
  `deletionPolicy: Retain` preserved the Kubernetes Secret, and the running app
  continued serving with that credential. Restoring the provider value returned
  the ExternalSecret to Ready/SecretSynced without credential loss.
- Both application workloads, all four HelmReleases and all ten Flux
  Kustomizations were Ready at capture time.

[Sanitized evidence](evidence/deployment-external-secrets-runtime-2026-11-01.json)
contains hashes, Pod UIDs, public-CA fingerprint, versions, tested Flux revisions
and boolean checks. Reproduction scripts and configuration remain in the new run
folder. No passwords, JWTs, client/root tokens, recovery shares or signing keys
were exported to Git. All seven prior run folders were removed as requested;
their historical configurations remain in Git history and findings were retained.

## Lab configuration correction

Disabling `serviceMonitor.enabled` alone did not permit this pinned ESO chart to
render without monitoring CRDs while inherited `renderMode` remained
`failIfMissing`. The run-owned override now also sets
`serviceMonitor.renderMode: skipIfMissing`. This preserves shared monitoring
requirements while allowing the intentionally focused lab to omit that stack.
The initial failing health wait held an older ConfigMap during reconciliation;
the exact committed override was applied to that ConfigMap and the HelmRelease
reconciled, after which the Flux stage reported Ready at the tested revision.
No shared application or credential Component needed a runtime fix.

## Scope

This is real in-cluster OpenBao → ESO → Kubernetes Secret → application delivery,
not a mocked backend. Tests used disposable randomized application credentials,
one 1Gi local-path-backed OpenBao replica and one lab recovery share/threshold.
Recovery material stayed in an owner-only VM file. Those are lab settings, not
shared production defaults or HA/custody recommendations.

The fixture replaces the echo starter with a real environment-reading Python
server returning only a hash. This does not test the nine application-specific
credential opt-ins against their full applications, actual upstream credential
rotation, OpenBao outage/recovery, CA rotation or external service integration.
Application restart after environment refresh is deliberately explicit; no global
restart controller was added.

Routine validation also passed: two new run DAGs, 70 compositions covering all
14 Components, nine application credential opt-ins/ten Secret contracts, 155
Kustomize builds and whitespace checks.

## Teardown

Report, evidence and configuration were published to both remotes in
`dbdd6314b92a5c14d70a053f47823bc6ee46808f` before playground destruction.
The destroy API confirmed success at **23:49:19 Europe/Istanbul**
(20:49:19 UTC). Both parallel validation playgrounds have been destroyed.
