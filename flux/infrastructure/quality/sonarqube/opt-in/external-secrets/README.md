# sonarqube: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `quality`. Store: `sonarqube-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `sonarqube-monitoring` | `infrastructure/quality/sonarqube/monitoring` | `passcode` |

This manages only the monitoring passcode. CNPG owns its application password. For a separately managed external PostgreSQL server, select `../external-database-secrets` as well.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
Apply this opt-in first to create its public bootstrap descriptor. With an
independently authenticated, TLS-verified OpenBao administrator session, provision
its backend from that **rendered** ConfigMap (replace the default namespace below
with the configured NS_QUALITY):


```sh
kubectl -n quality get configmap sonarqube-openbao-bootstrap -o jsonpath='{.data.policy\.hcl}' | bao policy write eso-quality-sonarqube -
kubectl -n quality get configmap sonarqube-openbao-bootstrap -o jsonpath='{.data.role\.json}' | bao write auth/kubernetes/role/eso-quality-sonarqube -
```

The policy also permits lookup, renewal and revocation of the authenticated
client's own short-lived token, required for ESO provider validation/lifecycle.
It grants no additional application paths or writes.

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/sonarqube-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.

Actual application credential consumption passed on fresh K3s. See
[runtime findings](../../../../../docs/findings/infra-eso-apps-2026-11-01.md).

Namespace placement, service DNS and backend role bindings follow the shared
[namespace mapping](../../../../../docs/operations/namespace-configuration.md). Do not apply raw role.json to OpenBao; it contains namespace placeholders.
