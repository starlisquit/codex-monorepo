# Redis Insight and NUI validation — 2026-11-01

## Result

Redis Insight's authenticated Redis API operations and persisted credentials
passed. NUI's NATS/JetStream API operations and persisted connections passed,
but its browser UI fails during startup. **NUI is not fully verified working**
and should not be enabled for users until that upstream issue is resolved.
Both templates are opt-in and excluded from full-platform deployment.

There is **no official Redis Insight Helm chart**. Redis's official installation
instructions provide Kubernetes manifests. The Redis Insight template adapts
those manifests rather than representing a third-party chart as official.
This is an explicit deviation from the requested Helm-only installation.

## Sources and versions

| Component | Official source | Pinned version |
| --- | --- | --- |
| Redis Insight | [Redis Kubernetes guide](https://redis.io/docs/latest/operate/redisinsight/install/install-on-k8s/) / [guide source](https://github.com/redis/docs/blob/main/content/operate/redisinsight/install/install-on-k8s.md) | image 3.8.0, pinned digest |
| NUI | [NUI project's chart](https://github.com/nats-nui/k8s), repository `https://nats-nui.github.io/k8s/helm/charts` | chart 0.1.6, image 0.10.0 |
| Redis fixture | Docker official `redis` image | 8.2.2-alpine |
| NATS fixture | [NATS official chart](https://github.com/nats-io/k8s) | chart 2.15.2 |

NUI maintainers label Kubernetes support experimental. The chart's appVersion
is `latest`; the template overrides it with a stable version explicitly.
Actual image IDs and sanitized results are in
[evidence/redis-nui-2026-11-01.json](evidence/redis-nui-2026-11-01.json).

## Focused playground

Fresh iximiuz K3s playground `6ae70fa356e9b785c32c7b89`, created
2026-11-01 13:08:35 Europe/Istanbul (10:08:35 UTC). Only the two UIs, a small
password-protected Redis fixture and one NATS server with JetStream were added.
The base playground supplies local-path storage and Kubernetes system services.
Browser tooling ran on the separate dev-machine. No platform observability,
Ceph, PKI or full-platform stack was deployed.

NATS used one replica and a 1Gi local-path JetStream PVC. This plaintext,
isolated broker fixture does not validate the existing platform NATS TLS
configuration. Redis was password protected; its data volume was intentionally
ephemeral because only UI Pods were replaced, not the Redis backend.
The UI PVCs were 1Gi for NUI and 2Gi for Redis Insight. No external provider
credentials, paid services or shared application data were used.

## Checks

23 functional assertions passed: 9 initial NUI, 6 initial Redis Insight and
8 recovery/schema checks. This count excludes the failed browser assertion.

- NUI imported a NATS CLI context from an external Kubernetes Secret and
  reported the pinned application version.
- NUI created a file-backed JetStream stream and published a message. The
  NATS CLI independently confirmed stored data and published a second message
  that NUI read back.
- NUI created a key/value bucket. A value written through NUI was read by the
  NATS CLI; a CLI write was read through NUI.
- Redis Insight rejected an invalid Redis password with HTTP 424 and the
  expected authentication error. A valid password-backed connection saved and
  connected successfully.
- Redis Insight wrote a string read independently with redis-cli. A redis-cli
  write was read through Redis Insight's string browser API.
- After deleting both UI Pods, a manually saved, non-imported NUI connection
  retained its ID, and JetStream messages and KV data remained accessible.
- Redis Insight retained its saved connection and decrypted its stored password
  using the same Secret after restart, then read the Redis value successfully.
- Both NUI schema-list endpoints returned HTTP 200 with empty arrays after the
  writable-path correction.

Redis Insight's initial settings screen rendered in Chromium. Functional
checks used its application API. Encryption was explicitly enabled and
analytics/notifications disabled in the disposable installation. The EULA
setting remained false; the complete interactive onboarding/database-browser
workflow was **not** claimed as verified. The initial encryption error was
resolved by supplying `RI_ENCRYPTION_KEY` and explicitly selecting encryption
in application settings; key availability alone is insufficient.

## NUI findings and changes

The official image defaults schema directories to `/protoschemas/default` and
`/cddlschemas/default`, which its application user cannot create. The template
passes explicit paths under the existing persistent `/db` volume through the
official entrypoint. This removes both schema endpoint HTTP 500 responses and
keeps schema files persistent without running the application as root.

A fresh Chromium profile still reports
`Cannot read properties of null (reading 'drawerPosition')` during startup.
Only the ALL/LOG/HELP/DRAWER shell renders; no usable connection view appears.
The failure reproduced with images 0.10.0, 0.9.3 and 0.8.1, so downgrading did
not provide a verified workaround. The final template and final running image
were restored to 0.10.0. Older images do not support all newer schema flags;
those compatibility errors during exploratory downgrades are not failures of
the final pinned configuration. Stuck experimental Helm upgrades were cleared
only in this disposable cluster. No upstream code was modified, no upstream
issue was filed and no browser-storage workaround was used to hide the failure.

Reproduce with a fresh browser profile at a port-forwarded NUI service and
inspect JavaScript errors. `/api/connection` and JetStream/KV endpoints continue
to work, demonstrating why readiness and API-only tests are insufficient for
this UI. Treat the template as experimental pending an upstream browser fix.

## Repository validation and reproduction

The standard validation script passes all 98 Kustomize builds and the existing
37 selected Flux child definitions / 25 selected HelmReleases. NUI's pinned
chart passes Helm lint and renders successfully with final values; its real
Helm deployment and subsequent Pod recovery were exercised. Redis Insight's
Kustomize output was applied directly and reached readiness. This focused run
does not claim end-to-end Flux controller reconciliation.

Use `flux/infrastructure/broker/nui/values.yaml` for NUI. Supply Secret
`broker/nui-contexts` with key `platform.json` containing a NATS CLI context.
For this lab only, its URL was `nats://nats.broker.svc.cluster.local:4222`.
Install the pinned NATS chart with JetStream enabled and local-path storage.
For Redis, use `flux/runbooks/examples/redisinsight-validation-backend.yaml`
and first create a random-password Secret `ui/redis-validation` with key
`password`. Create `ui/redisinsight-encryption` with key `key` before applying
`flux/infrastructure/ui/redisinsight`. Keep all generated credentials outside
Git. Configure encryption explicitly in the initial application settings.

The template READMEs describe production authentication/TLS requirements and
private access. The isolated fixture does not validate Redis Enterprise,
Valkey TLS, NATS TLS/creds-file authentication, ingress authorization, backend
failover, backup/restore or production load.

## Teardown

Findings and configuration must be committed and pushed to both GitHub and
GitLab before playground destruction. Confirmed destruction is recorded in a
follow-up commit after the destroy API succeeds.
