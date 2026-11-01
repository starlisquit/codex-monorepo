# ClickHouse cluster

Select this base separately from `../operator`. It creates a `KeeperCluster`
and `ClickHouseCluster` named `clickhouse` in `databases`, using the official
`clickhouse.com/v1alpha1` API and the database image digests verified with
operator `0.0.8`.

Defaults: three Keeper replicas, one ClickHouse shard with two replicas,
and 20Gi `ceph-block` PVCs per pod. Patch storage class, capacity, sizing and
placement for the consuming cluster. These replica counts provide redundancy;
node failure tolerance also requires appropriate pod placement and storage.

Prerequisites:

- Select `infrastructure/namespaces/databases`.
- Reconcile `infrastructure/databases/clickhouse/operator` and its prerequisites.
- Supply Secret `clickhouse-auth` in `databases`, with key `password`, using
  your secret management workflow. No password is included in this base.
- Provide `ceph-block` storage or patch the storage class.

Use a separate Flux Kustomization depending on the operator stage, with
health checks for both `clickhouse.com/v1alpha1` kinds and a Ready condition
expression, as in the retained ClickHouse validation run. Set `prune: false`
for the database stage if removing it from Git must not delete database CRs.
Changing metadata names also requires updating `keeperClusterRef` and the
password Secret reference where applicable.

The operator manages inter-node NetworkPolicies. Add explicitly scoped client
access rules for your applications; this base adds no ingress or LoadBalancer.
Database TLS and backups must be configured for your environment.

Validation: this base builds and validates against the pinned official CRD
schemas. The earlier [live verification](../../../../docs/findings/clickhouse-operator-2026-11-01.md)
tested these images with one ClickHouse and one Keeper replica, SQL and pod
replacement persistence. The larger topology, Ceph storage and password Secret
configuration in this reusable base have not been live-tested.

## Optional OpenBao credentials (clickhouse)

Select [the credential opt-in](opt-in/external-secrets/README.md) to supply its
existing Secret references through External Secrets instead of manual provisioning.
