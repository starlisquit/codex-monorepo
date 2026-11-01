# ClickHouse operator verification — 2026-11-01

Verified the official ClickHouse Inc operator through Flux in a fresh, focused
iximiuz K3s playground. This is the ClickHouse operator, not Altinity's operator.

## Versions and configuration

- Template: `infrastructure/databases/clickhouse/operator`.
- Official upstream: https://github.com/ClickHouse/clickhouse-operator
- Official OCI chart: `oci://ghcr.io/clickhouse/clickhouse-operator-helm:0.0.8`;
  application `v0.0.8`.
- Chart digest: `sha256:61d97bb43a16859f485af1099251fc591b527a4c01013e6de355be11a80fbc9c`.
- Kubernetes: `v1.37.1+k3s1`; Flux `v2.10.0`; cert-manager chart `v1.21.3`.
- Managed ClickHouse and Keeper: `26.10.3.7`. The test fixture pins the observed
  image digests, since the operator's upstream database defaults use `latest`.
- Playground: `6ae76eb246471e13268a2db6`.
- Flux path: `./flux/clusters/20261101-195410-clickhouse-operator-8a2db6`.
- Final tested configuration revision: `9c3c0b38cdc83aa5d7dc6189f56a127fc0cd4ece`.
- Evidence captured at 20:00 Europe/Istanbul (17:00 UTC):
  [sanitized Kubernetes status](evidence/clickhouse-operator-2026-11-01.json).

## Results

- Helm lint passed; chart rendered with the shared template values.
- Repository validation passed: 131 Kustomize builds, both retained run folders,
  source/namespace coverage and Flux dependency DAG checks.
- Flux read the exact fresh run folder from Git and reconciled foundation,
  cert-manager, operator and workload stages to the tested revision. All Ready.
- Operator Deployment Ready, no restarts. Both official
  `clickhouse.com/v1alpha1` CRDs installed and reconciled.
- Webhook and metrics certificates Ready. Server-side admission produced the
  upstream warnings for a deliberately incomplete dry-run fixture, confirming
  webhook invocation. A negative replica count was rejected by CRD schema
  validation. A zero replica count is accepted; do not assume zero is invalid.
- One Keeper and one ClickHouse replica became Ready, each using a bound 1Gi
  local-path PVC. Both custom resources report observed generation 2 after the
  image pinning update, matching their desired generations.
- Created `validation.operator_check` using `ReplicatedMergeTree` with a Keeper
  path, inserted `(1, 'clickhouse-operator-verified')`, and read the exact row.
- `system.replicas`: `is_readonly=0`, `is_session_expired=0`,
  `total_replicas=1`, `active_replicas=1`: the table has an active Keeper session.
- Deleted ClickHouse pod UID `bb6ce44d-9a0d-412b-994d-0bfac71eb617`.
  StatefulSet recreated it with UID `d1bb7560-ba3b-4c79-8c89-f20f1448b004`.
  After readiness, the same row remained on its existing PVC. SQL and Keeper
  session checks passed again after Flux applied the pinned image fixture.

SQL checks used the official `clickhouse-client` inside the managed pod:

```sql
CREATE DATABASE IF NOT EXISTS validation;
CREATE TABLE validation.operator_check (id UInt64, value String)
ENGINE=ReplicatedMergeTree('/validation/operator_check', 'replica1') ORDER BY id;
INSERT INTO validation.operator_check VALUES (1, 'clickhouse-operator-verified');
SELECT id,value FROM validation.operator_check;
SELECT is_readonly,is_session_expired,total_replicas,active_replicas
FROM system.replicas WHERE database='validation';
```

## Scope and observations

The shared template installs only the operator; it does not implicitly create a
database. Namespace/source bases remain independently selectable. cert-manager
is an explicit HelmRelease dependency, and optional cluster values use the native
`clickhouse-operator-cluster-values` ConfigMap. No monitoring stack is needed by
the ClickHouse template. The run disabled the shared cert-manager monitoring
integration to keep the playground focused.

The test fixture is non-HA, uses local-path storage and upstream default database
authentication/TLS (passwordless default user, no database TLS). No external
access was exposed; SQL ran inside the database pod. Production consumers must
configure credentials, network access, TLS, storage and replica counts. External
client connectivity, HA, backup/restore, load and upgrades were not tested.

The chart's self-signed certificate requests emitted cert-manager's empty Issuer
DN warning. Certificates issued and admission worked; strict external TLS clients
were not tested. Startup briefly reported missing metrics certificate before
cert-manager issued it; it recovered without intervention.

## Teardown

Findings and configuration published to both remotes at identical commit
`8a2630910541050b159f07be237cd24fa4ada874` before destruction.
The destroy API returned `ok: true` at 20:00:48 Europe/Istanbul
(17:00:48 UTC). The playground was destroyed, not stopped.

## Reusable cluster base

Added `infrastructure/databases/clickhouse/cluster` as a separately selectable
base containing both `KeeperCluster` and `ClickHouseCluster`, named `clickhouse`
in `databases`. It reuses the verified image digests and defaults to three Keeper
replicas, one shard with two ClickHouse replicas, and 20Gi ceph-block PVCs per pod.
The default user password references externally supplied Secret `clickhouse-auth`
key `password`; no credentials are committed.

Both manifests validate against the official chart 0.0.8 CRD OpenAPI schemas;
all 132 repository Kustomize builds pass. This is static schema/build validation:
the larger topology, Ceph storage and Secret-based default user password have not
been live-tested. The previous live verification remains scoped to its original
single-replica run. No new playground was created for this extraction.
