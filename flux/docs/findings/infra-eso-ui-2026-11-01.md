# Infrastructure ESO: RedisInsight and NUI

**Passed.** Fresh K3s playground `6ae7a6d17f32053bde2c28eb`, created alongside
three other focused runs. Flux path:
`flux/clusters/20261101-235337-infra-eso-ui-2c28eb`.
Application checks completed **2026-11-02 00:06:53 Europe/Istanbul**
(2026-11-01 21:06:53 UTC). Policy fix: `b394d1e`; final reconciled configuration: `de6fab5`.
All selected Flux stages and HelmReleases were Ready at final capture.

## Real application results

- Both application-specific SecretStores and ExternalSecrets authenticated with
  their supplied roles/policies. Their generated Secrets matched every provider
  property and had the correct ExternalSecret owner reference.
- `ui/redisinsight-encryption:key` came from OpenBao. The real RedisInsight 3.8.0
  application enabled encryption, saved a password-authenticated Redis connection,
  and used its data API to write/read a key. Independent `redis-cli` confirmed
  the write. After Pod replacement it reused that saved encrypted connection
  and repeated the operations, proving the retained encryption key worked.
- `broker/nui-contexts:platform.json` came from OpenBao. NUI 0.10.0/chart0.1.6
  autoloaded that NATS CLI context and its token, then created a JetStream stream
  and published data through its real API. Stream state confirmed stored messages.
  After Pod replacement it retained the connection identity and authenticated
  broker operations still worked.
- Each scoped identity could read its own path; unrelated KV paths and wrong
  token audiences were rejected. No application-specific ESO ownership overlapped
  PKI, a broker/operator-owned Secret or another opt-in.

## Runtime fix found across infrastructure integrations

The initial application policies omitted `auth/token/lookup-self` while setting
`token_no_default_policy: true`. ESO rejected every store with
`InvalidProviderConfig`; its provider validation received HTTP403 on self-lookup.
All nine infrastructure opt-in policies now explicitly permit read on lookup-self
and update on renew-self/revoke-self. These operations affect only the caller's
own token; existing exact-path KV read-only scope is preserved. Routine validation
checks this complete policy contract. This fix was applied through the real
OpenBao API before retesting; the Secret delivery/application results above
were obtained after the correction.

## Evidence and scope

[Sanitized evidence](evidence/infra-eso-ui-2026-11-01.json) includes credential
hashes, contract/auth checks, application results, chart versions and Pod IDs.
The run's probes preserve the setup and API checks. Raw credentials, tokens,
root/unseal material and encryption keys were not committed.

K3s `v1.37.1+k3s1`, cert-manager `v1.21.3`, trust-manager `v0.26.0`, OpenBao
chart0.30.6/server2.7.2 and ESO2.14.0 provided real in-cluster delivery.
Isolated fixtures used Redis8.2.2-alpine and NATS2.12.1-alpine with authentication.
These fixture connections do not verify platform Valkey/NATS TLS. This run
verified credential consumption and persistence through real application APIs;
the earlier browser suite remains documented separately and was not rerun here.
The harness was corrected to update an existing Redis key after restart rather
than treating the expected create-conflict HTTP409 as a credential failure.

One disposable OpenBao replica used a 1Gi local-path volume and lab-only recovery
custody; no HA, root-CA rotation or encryption-key rotation is claimed. Subsequent
source revisions contain other lane fixtures/reports; Flux stage metadata in the
evidence distinguishes their propagation from the tested workload revision.

## Teardown

Findings/configuration were published to both remotes in
`2cef441f92244cdac89314d1bd3e041706e4bcbf` before teardown.
Destroy API confirmed playground destruction at `2026-11-01T21:11:56Z`.
