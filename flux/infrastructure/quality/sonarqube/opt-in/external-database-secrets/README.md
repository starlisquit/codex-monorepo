# sonarqube-external-database: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `quality`. Store: `sonarqube-external-database-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `sonarqube-database` | `infrastructure/quality/sonarqube/database` | `password` |

Only for the base external-database mode. Do not select with the CNPG PostgreSQL integration. Provision/change the actual database password independently, and configure its JDBC endpoint/user in cluster values.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
With an independently authenticated, TLS-verified OpenBao administrator session,
apply the narrowly scoped backend configuration from this directory:

```sh
bao policy write eso-quality-sonarqube-external-database policy.hcl
bao write auth/kubernetes/role/eso-quality-sonarqube-external-database @role.json
```

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/sonarqube-external-database-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.
