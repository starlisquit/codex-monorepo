# Deployment OpenBao injector: K3s runtime verification

**Passed.** Playground `6ae7a35146471e132691ca0a`, created concurrently with the
ESO playground. Flux reconciled only
`flux/clusters/20261101-233841-deployment-injector-91ca0a` at tested configuration
`4bfce4a958eb154128833151e3279acc54d76e2c`. Evidence captured at **23:47:21
Europe/Istanbul**, 2026-11-01 (20:47:21 UTC).

Versions: K3s `v1.37.1+k3s1`, Flux `2.10.0`, cert-manager `v1.21.3`,
trust-manager `v0.26.0`, official OpenBao chart `0.30.6`, OpenBao/agent `2.7.2`
and chart-provided `vault-k8s:1.7.6` injector. Only the relevant controller,
PKI/trust, one OpenBao Raft replica and two application fixtures were deployed.

## Actual runtime results

- The Component's prefixed service accounts and role annotations authenticated
  independently for `api` and `worker` in namespace `demo`.
- Each injected init agent rendered `/vault/secrets/config.json`; each continuing
  agent refreshed it. The real non-root application read the JSON file and
  returned a SHA-256 fingerprint matching its randomized OpenBao value.
- File permissions were **0400**, owned by **UID10001**. Both application Pods
  included the expected init agent and continuing agent. The projected login
  token was mounted in agent containers and absent from the application container;
  automatic service-account token mounting remained disabled.
- OpenBao communication succeeded with TLS verification and the central public
  CA. The application did not receive any PKI private key or OpenBao root token.
- A service-account JWT authenticated to its assigned role and read its own path.
  Cross-application reads, wrong service account, same-named account in the wrong
  namespace, and wrong audience all returned **HTTP403**. Self lookup and renewal
  worked under the explicit token-lifecycle policy permissions.
- Changing only the API app's provider value refreshed its file without changing
  its Pod UID. The worker's fingerprint and Pod UID remained unchanged.
- A temporary injected workload requesting a forbidden KV path remained in init;
  the agent reported permission denial and its application never started. The
  fixture was deleted afterwards.
- The API agent logged multiple successful authentications under lab-specific
  **30s token TTL / 2m maxTTL**, continuing with the same application Pod UID and
  correct credential fingerprint. This verifies renewal/reauthentication behavior
  rather than relying on a single successful initial login.
- Both application workloads, every selected HelmRelease and all nine Flux
  Kustomizations were Ready at capture time.

[Sanitized evidence](evidence/deployment-injector-runtime-2026-11-01.json) includes
hashes, Pod UIDs, public-CA fingerprint, chart versions, Flux revisions and boolean
checks. Scripts and selected configuration are retained in the new run folder.
No credential values, JWTs, client/root tokens, unseal shares or signing keys were
exported to Git. All seven prior run folders were removed as requested; previous
findings remain and prior configurations are available in Git history.

## Scope and lab overrides

The lab enabled fail-closed admission and a **5s static-secret rendering interval**
to make observation quick. It used one 1Gi local-path-backed OpenBao replica and
one lab recovery share/threshold, kept only in an owner-only VM file. These are
focused disposable-test settings, not changes to shared production defaults.

The fixture replaces the echo starter with a Python application that actually
reads the credential file; it exposes only a hash. No real upstream credential
rotation, HA/recovery exercise, root-CA rotation, injector-outage admission test,
full application/browser suite or projected-token expiry test is claimed. The
forbidden-path test verifies init blocking **after successful admission injection**.
No competing controller-managed Secret was created or adopted by this Component.

## Teardown

Report, evidence and configuration were published to both remotes in
`f1a969508488fec91bab0aa83acd3f06b640a885` before playground destruction.
The destroy API confirmed success at **23:48:11 Europe/Istanbul**
(20:48:11 UTC).
