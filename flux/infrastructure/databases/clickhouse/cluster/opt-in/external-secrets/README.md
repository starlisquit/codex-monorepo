# clickhouse: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `databases`. Store: `clickhouse-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `clickhouse-auth` | `infrastructure/databases/clickhouse/auth` | `password` |

This supplies the existing default-user password reference. It does not manage Keeper, operator webhook or TLS Secrets. Verify database-side password reload/reconciliation before declaring a rotation complete.

Read the [shared setup, ownership and rotation contract](../../../../../../docs/operations/application-external-secrets.md) first.
With an independently authenticated, TLS-verified OpenBao administrator session,
apply the narrowly scoped backend configuration from this directory:

```sh
bao policy write eso-databases-clickhouse policy.hcl
bao write auth/kubernetes/role/eso-databases-clickhouse @role.json
```

The policy also permits lookup, renewal and revocation of the authenticated
client's own short-lived token, required for ESO provider validation/lifecycle.
It grants no additional application paths or writes.

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/clickhouse-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.

Live OpenBao/ESO delivery and actual application credential use passed on fresh
K3s. See [runtime findings](../../../../../../docs/findings/infra-eso-data-2026-11-01.md).
