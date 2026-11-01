# Optional PostgreSQL for LiteLLM

This opt-in supplies a `postgresql.cnpg.io/v1` **Cluster custom resource** for
CloudNativePG. The operator's official Helm chart installs the CRD/controller
once per Kubernetes cluster; this directory does not vendor a second CRD or
install another operator for LiteLLM.

## What is deployed

`cluster.yaml` creates `ai/litellm-db`: PostgreSQL 18.6 (official CNPG image),
three instances, 20Gi ceph-block storage per instance, database `litellm` and
owner `litellm`. Superuser remote access is disabled. Configure storage class,
capacity, replica count and resources for the deployment before selecting it.

CNPG generates the application Secret `litellm-db-app` and TLS CA Secret
`litellm-db-ca`; no database password is committed or manually copied.
The normal read/write endpoint is `litellm-db-rw.ai.svc.cluster.local`.
The operator manages server certificates and replication TLS, so this opt-in
does not require the separate platform cert-manager PKI bundles.

`integration/` is a second, separately selectable Kustomization. It creates
watch-labelled ConfigMap `ai/litellm-postgresql-values`, which the shared
LiteLLM HelmRelease references optionally between shared defaults and
cluster-owned overrides. The merge order is:

1. Shared LiteLLM defaults.
2. This optional PostgreSQL integration.
3. Optional `litellm-cluster-values` supplied by the cluster.
4. Inline HelmRelease values, if any.

The integration enables the existing-database path, reads the generated app
Secret, mounts **only ca.crt**, and uses Prisma's strict TLS settings for
server trust and hostname verification. Neither the CA signing key nor a
superuser credential is mounted into LiteLLM. Both the proxy and migration Job
receive the same URL and public CA. If overriding volumes/mounts in cluster
values, retain that CA mount; Helm replaces lists rather than merging entries.

## Enable in database-first order

Prerequisites: select `infrastructure/namespaces/ai`; install the shared CNPG
operator using its namespace/source and documented monitoring prerequisites;
ensure the chosen StorageClass can provision PVCs. Select LiteLLM's OCI source
and provision its normal auth/provider Secrets as described in the parent README.

1. Select this directory in a dedicated database Flux Kustomization. It contains
   only the Cluster resource, not the integration ConfigMap or application.
2. Wait for Cluster `ai/litellm-db` to report Ready, with generated Secrets.
3. Ensure `ai/litellm-auth` contains the existing stable `master-key` and an
   additional high-entropy, persistent `salt-key`. Retain both through upgrades
   and restores. Provision these outside Git; do not regenerate them on rollout.
4. Select `integration/` only after the database readiness gate. Its ConfigMap
   enables DB mode in an existing LiteLLM release through the normal watch,
   without replacing the cluster's separate override ConfigMap.

For a focused manual lab with the operator and Secrets already provisioned:

```sh
kubectl apply -k flux/infrastructure/namespaces/ai
kubectl apply -k flux/infrastructure/ai/litellm/opt-in/postgresql
kubectl -n ai wait cluster/litellm-db --for=condition=Ready --timeout=15m
kubectl apply -k flux/infrastructure/ai/litellm/opt-in/postgresql/integration
```

For GitOps, the database Kustomization should depend on the namespace/storage
foundation and CNPG operator. Use prune:false for the stateful database and
an explicit Cluster health check. The integration Kustomization then depends
on that database Kustomization. For example, its database health gate can use:

```yaml
healthChecks:
- apiVersion: postgresql.cnpg.io/v1
  kind: Cluster
  name: litellm-db
  namespace: ai
healthCheckExprs:
- apiVersion: postgresql.cnpg.io/v1
  kind: Cluster
  current: has(status.conditions) && status.conditions.exists(c, c.type == 'Ready' && c.status == 'True')
```

Do not place the integration ConfigMap in the first DB reconciliation: an
already-running LiteLLM HelmRelease watches it immediately and would switch
before the database is ready. The two directories make that ordering explicit.
The base template selects neither directory and remains database-free.

## Migrations and operations

The integration enables the official chart's Helm pre-install/pre-upgrade
migration hook and disables its Argo CD annotation. The proxy is configured by
the chart to skip concurrent schema updates; the migration Job owns that work.
The Job gets a 10-minute deadline, 512Mi request and 2Gi memory limit. A 1Gi
limit was insufficient in the focused live test. Preserve the stable database
and auth Secrets and back up the database before schema-changing upgrades.
Do not run a PostgreSQL major upgrade by casually changing the image tag.

Three instances are not an off-cluster backup. No backup bucket, WAL archiving,
PITR policy or external backup credentials are configured here. Storage and
backup/restore policy remain deployment decisions. A removed integration
ConfigMap returns the proxy to its remaining configuration layers; it does
not migrate database-backed keys into database-free mode or delete the database.

See [deployment verification](../../../../../docs/findings/litellm-postgresql-2026-11-01.md)
for tested behavior, lab overrides and limits.
