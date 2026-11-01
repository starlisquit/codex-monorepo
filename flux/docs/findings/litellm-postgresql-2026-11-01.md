# LiteLLM PostgreSQL opt-in — 2026-11-01

## Result and implementation

Added a deployable CloudNativePG Cluster at
`infrastructure/ai/litellm/opt-in/postgresql/cluster.yaml`, replacing the former
values-only example. The base LiteLLM deployment remains database-free and
neither the database nor its integration is selected automatically.

The opt-in creates `ai/litellm-db`, PostgreSQL 18.6 using the official CNPG
image, three instances and a 20Gi ceph-block PVC per instance. CNPG generates
the dedicated `litellm` role/application Secret and TLS certificates. Superuser
remote access is disabled. The operator chart installs the Cluster CRD once;
this is an application Cluster custom resource, not another CRD definition.

The separately selectable `integration/` directory generates the optional
`litellm-postgresql-values` ConfigMap after database readiness. The HelmRelease
reads it between defaults and cluster overrides. Existing cluster overrides
remain independently owned and retain precedence. The integration uses the
generated app Secret, mounts only the public CA, requires strict Prisma TLS,
loads a stable salt key from the existing auth Secret, and enables the official
chart's Helm migration hook. Parent and opt-in READMEs explain namespace/source
selection, credentials, migration gating and operational limits.

## Focused live validation

Fresh K3s playground `6ae7603746471e132687f4f5` was created at
2026-11-01 15:52:23 UTC / 18:52:23 Europe/Istanbul. Only the CNPG operator,
LiteLLM and this PostgreSQL cluster were added. No Ceph, full observability,
cert-manager/PKI or external model provider was deployed.

Versions: CloudNativePG chart 0.29.1, PostgreSQL
`ghcr.io/cloudnative-pg/postgresql:18.6-system-trixie`, LiteLLM official OCI chart
1.106.6. LiteLLM chart digest:
`sha256:b681a4cb1eafd4c8aa642b58e9666d9f8afb9c4972d2230d91b2b1dfecf8f934`.
The CNPG operator's monitoring PodMonitor was disabled for the focused lab;
all three database instances were retained. Database storage was overridden
before successful bootstrap to local-path / 1Gi per instance. These lab settings
do not change the shared operator or database defaults.

16 functional assertions passed: four initial API checks, five Prisma/TLS
checks and seven recovery checks. SQL inspections independently confirmed 213
completed migrations, a non-superuser application role and encrypted application
connections. [Sanitized evidence](evidence/litellm-postgresql-2026-11-01.json)
contains the assertions, image IDs, Pod UIDs and integration values hash.

| Check | Observed result |
| --- | --- |
| CNPG admission and bootstrap | Cluster accepted by the installed official CRD; all three instances became Ready |
| Generated credentials | App Secret litellm-db-app and CA Secret litellm-db-ca were generated without committed passwords |
| Chart wiring | Proxy and migration Job read the same app Secret, DB endpoint and public-only CA mount |
| Migration hook | Successful Helm pre-install migration completed; database contains 213 completed migrations |
| Proxy DB readiness | HTTP 200, status healthy, db connected |
| Authentication | Invalid key rejected in database mode; a new DB-backed virtual key generated and authenticated |
| Least-privilege application role | SQL current_user = litellm and pg_roles.rolsuper = false |
| Database encryption | pg_stat_ssl showed encrypted connections for the application role |
| Strict trust | Prisma connection with an unrelated CA was rejected |
| Strict identity | Connecting to the Service IP with the correct CA was rejected for an IP/hostname mismatch |
| Recovery exercise | Proxy Pod and PostgreSQL primary Pod deleted; CNPG promoted litellm-db-2 from litellm-db-1 |
| Persistent state | After all three DB instances recovered and a new proxy Pod became Ready, the previously generated virtual key still authenticated; its database row remained present |

The recovered proxy had a different UID. The original primary Pod also had a
different UID and returned as a replica. The test checks recovery after a
controlled Pod deletion, not uninterrupted availability or storage-node failure.
The exact pre/post identities are recorded in the evidence.

A dummy provider credential was used only to satisfy the base configuration.
No inference/provider requests were made. The checks exercise actual database
migrations, application authentication, Prisma and PostgreSQL rather than a mock
DB. The integration ConfigMap's contents matched the values file used by the
live Helm install, and its hash matches the committed repository input. Helm
was used directly in the focused lab; a new end-to-end Flux reconciliation run
is not claimed.

## Findings resolved during verification

The first migration Job was OOM-killed under a 1Gi limit. The integration now
requests 512Mi and allows 2Gi; that Job completed without a restart. A steady
proxy snapshot used about 574Mi and database instances about 56–80Mi each;
these observations are not production sizing guarantees. The schema migration
process must not be sized from the proxy's idle memory alone.

CNPG correctly rejected a test attempt to shrink a newly declared 20Gi volume
to 1Gi. The uninitialized fixture was recreated with lab storage overrides
before successful bootstrap. Apply lab/storage overrides before creation;
volume shrinking is not an operational procedure provided by this template.

The upstream LiteLLM chart defaults extraEnvVars to a map but consumes a list;
Helm lint emits a coalescing warning when setting the salt-key list. Rendering
and live installation verified the correct environment entries in both proxy
and migration Job; lint passed. The warning was not treated as proof of failure
or used to skip the environment/TLS checks.

## Repository checks and limits

All 150 Kustomize builds and the existing 37 selected child definitions / 25
selected HelmRelease readiness coverage checks passed. The pinned chart passed
Helm lint/render with final integration values. The default chart render has
no PostgreSQL StatefulSet, migration Job or DATABASE_URL. The opt-in root
renders only the Cluster, while integration renders only its ConfigMap. The
base references that ConfigMap optionally, preserving the default behavior.

The Cluster remains outside the full-platform selection. Storage/replica
sizing, backups, WAL archiving/PITR, provider inference, spend/budget behavior,
admin UI, load and full Flux upgrade reconciliation were not validated. The
current user has no external test bucket; backup/restore is not configured or
claimed here. Retain master/salt keys and database backups for recovery.

## Other templates that would benefit

| Priority | Template | Suggested opt-in improvement |
| --- | --- | --- |
| 1 | SonarQube | Dedicated CNPG Cluster, generated application credentials, TLS JDBC settings and readiness gating. Its current template requires external PostgreSQL, so this closes an immediate deployment gap. |
| 2 | Grafana in the observability stack | Optional shared PostgreSQL backend for Grafana state when deploying multiple Grafana replicas, with credentials/TLS and DB-first readiness. Useful for an HA configuration rather than every single-instance installation. |
| 3 | LiteLLM | Optional dedicated Valkey/Redis integration for shared caching and coordination when scaling replicas/workers, using explicit TLS/auth settings and keeping the one-worker base small. |
| 4 | NUI and Redis Insight | Opt-in connection profiles and credential/CA integration for the already-selected NATS/Valkey backend. Reuse the selected broker/database instead of creating a new backend merely for an administration UI. |

These are recommendations only; this change implements the LiteLLM PostgreSQL
opt-in. SonarQube is the most direct next use of the same Cluster pattern.

## Publication and teardown

Implementation, findings and evidence were committed as `6128953` and pushed
to both GitHub and GitLab; remote main commit IDs matched before teardown.
The explicit destroy API returned `ok: true` for playground
`6ae7603746471e132687f4f5` at 2026-11-01 16:11:43 UTC / 19:11:43
Europe/Istanbul. It was destroyed, not stopped; the immediate listing reported
it non-running while deletion propagated.
