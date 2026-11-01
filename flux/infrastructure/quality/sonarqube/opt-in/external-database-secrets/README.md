# sonarqube-external-database: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `quality`. Store: `sonarqube-external-database-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `sonarqube-database` | `infrastructure/quality/sonarqube/database` | `password` |

Only for the base external-database mode. Do not select with the CNPG PostgreSQL integration. Provision/change the actual database password independently, and configure its JDBC endpoint/user in cluster values.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
Apply this opt-in first to create its public bootstrap descriptor. With an
independently authenticated, TLS-verified OpenBao administrator session, provision
its backend from that **rendered** ConfigMap (replace the default namespace below
with the configured NS_QUALITY):


```sh
kubectl -n quality get configmap sonarqube-external-database-openbao-bootstrap -o jsonpath='{.data.policy\.hcl}' | bao policy write eso-quality-sonarqube-external-database -
kubectl -n quality get configmap sonarqube-external-database-openbao-bootstrap -o jsonpath='{.data.role\.json}' | bao write auth/kubernetes/role/eso-quality-sonarqube-external-database -
```

The policy also permits lookup, renewal and revocation of the authenticated
client's own short-lived token, required for ESO provider validation/lifecycle.
It grants no additional application paths or writes.

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/sonarqube-external-database-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.

The externally supplied database-password mode passed real SonarQube project
creation and an independent PostgreSQL persistence check. See
[runtime findings](../../../../../docs/findings/infra-eso-apps-2026-11-01.md).

Namespace placement, service DNS and backend role bindings follow the shared
[namespace mapping](../../../../../docs/operations/namespace-configuration.md). Do not apply raw role.json to OpenBao; it contains namespace placeholders.
