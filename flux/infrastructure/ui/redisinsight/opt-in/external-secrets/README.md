# redisinsight: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `ui`. Store: `redisinsight-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `redisinsight-encryption` | `infrastructure/ui/redisinsight/encryption` | `key` |

Keep the encryption key stable and backed up independently. Changing it can make existing saved credentials unreadable; this is not an automatically rotatable password.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
Apply this opt-in first to create its public bootstrap descriptor. With an
independently authenticated, TLS-verified OpenBao administrator session, provision
its backend from that **rendered** ConfigMap (replace the default namespace below
with the configured NS_UI):


```sh
kubectl -n ui get configmap redisinsight-openbao-bootstrap -o jsonpath='{.data.policy\.hcl}' | bao policy write eso-ui-redisinsight -
kubectl -n ui get configmap redisinsight-openbao-bootstrap -o jsonpath='{.data.role\.json}' | bao write auth/kubernetes/role/eso-ui-redisinsight -
```

The policy also permits lookup, renewal and revocation of the authenticated
client's own short-lived token, required for ESO provider validation/lifecycle.
It grants no additional application paths or writes.

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/redisinsight-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.

Live OpenBao/ESO delivery and actual application credential use passed on a fresh
K3s run. See [runtime findings](../../../../../docs/findings/infra-eso-ui-2026-11-01.md).

Namespace placement, service DNS and backend role bindings follow the shared
[namespace mapping](../../../../../docs/operations/namespace-configuration.md). Do not apply raw role.json to OpenBao; it contains namespace placeholders.
