# Infrastructure ESO: ClickHouse and Velero

**Passed.** Fresh K3s playground `6ae7a6d346471e1326921fed`, created alongside
three other focused infrastructure runs. Flux path:
`flux/clusters/20261101-235339-infra-eso-data-921fed`. Final selected configuration
is `d18e8d7819bf921edb84c52df0205c49627a7086`; policy correction is `b394d1e`.
Final application verification completed at 2026-11-01 21:19:40 UTC; evidence
was captured at 21:21:00 UTC (2026-11-02 00:21:00 Europe/Istanbul), with all
selected Flux stages and HelmReleases Ready.

## Actual application results

Both namespace-local stores/ExternalSecrets authenticated to real OpenBao and
created their exact target Secret contracts, with matching provider values and
ExternalSecret ownership. Each role could read its own path; unrelated KV reads
and wrong token audiences were rejected.

- Official ClickHouse operator0.0.8 deployed ClickHouse26.10.3.7 and one Keeper
  replica using run-owned local-path/1Gi sizing overrides. The real
  `defaultUserPassword.secret` reference consumed `databases/clickhouse-auth`.
  A deliberately wrong password was rejected. The ESO-provided password allowed
  SQL database/table creation, insertion and a successful independent SELECT.
- Official Velero chart12.2.2/app1.18.2 with AWS plugin1.14.4 mounted
  `velero/velero-cloud-credentials:cloud`. Its actual BackupStorageLocation became
  **Available** against an authenticated local SeaweedFS S3 endpoint.
- Velero backed up a disposable namespace/ConfigMap. The Backup completed without
  errors; a separately signed S3 listing found its object prefix. After deleting
  the ConfigMap, a real Velero Restore completed and recreated its expected data.
  This proves the application used the delivered shared-credentials file for
  actual object-storage writes and reads, beyond merely mounting a Secret.
- The corrected run was reconciled through its own Flux path. Setup/probe scripts,
  exact selected values, contract checks and sanitized runtime evidence are retained.

## Shared policy fix

Initial policies for all nine infrastructure opt-ins disabled the default OpenBao
policy but omitted self-lookup required by ESO provider validation. Stores failed
with HTTP403 at `auth/token/lookup-self`. The policies now explicitly allow
lookup/renew/revoke of the caller's own token, retaining exact-path, read-only KV
access. Both integrations passed after applying the corrected backend policies.
Routine validation now checks that complete contract. No certificate, CA/private
key, CNPG credential or competing controller-owned Secret was adopted by ESO.

## Local fixture corrections

The originally selected MinIO images could not be anonymously pulled from either
registry. The lab now uses official SeaweedFS4.00 pinned to digest
`sha256:dcbccdc9f33689d43ca3d1fb73d2baa319f8307c59d7923191b993ddc85ba6f8`.
Its random access/secret keys are supplied only through a disposable fixture
Secret, while Velero's copy travels through OpenBao and ESO.

A first one-volume budget left no writable slot for the S3 bucket's collection,
so an initial backup failed during object writes despite successful authentication
and BSL availability. The corrected fixture permits 16 small 10MiB volumes,
uses Recreate, gates readiness on the S3 TCP listener, and the probe waits for a
signed request before proceeding. Backup/restore was rerun after those fixes.
The AWS checksum settings were not weakened. These changes affect only the
isolated test fixture; shared Velero/application defaults are unchanged.

During fixture correction the S3 Flux stage was temporarily suspended to avoid
reapplying its previous broken image/storage settings. The exact committed Velero
wrapper was initially applied directly while dependency revision propagation
caught up. The S3 stage was resumed and all selected stages reconciled at `d18e8d7`
before the final source-consistent verification and capture.

## Scope and evidence

[Sanitized evidence](evidence/infra-eso-data-2026-11-01.json) contains Secret
fingerprints, contract/auth results, actual application results, chart versions,
Pod identities and Flux source/readiness metadata. Credentials, JWTs, OpenBao root
and unseal material, and signing keys were not exported to Git.

K3s `v1.37.1+k3s1`, cert-manager1.21.3, trust-manager0.26.0,
OpenBao2.7.2/chart0.30.6 and ESO2.14.0 provided the shared services. The focused
lab used one small OpenBao replica, one ClickHouse/Keeper replica and ephemeral
S3 fixture storage. No production HA, independent disaster recovery, PVC backup/
restore, database TLS, upstream credential rotation or external-bucket validation
is claimed. Local HTTP S3 is an isolated fixture override; the reusable S3 example
continues to use HTTPS. An external production bucket remains separately unverified.

## Teardown

Findings/configuration were published to both remotes in
`437e01e252462f045a4eb2e55f3f238a5ad953bb` before teardown. The destroy API
confirmed destruction at `2026-11-01T21:21:18Z`
(2026-11-02 00:21:18 Europe/Istanbul). All four infrastructure verification
playgrounds were destroyed after their findings were published.
