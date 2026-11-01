# velero: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `velero`. Store: `velero-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `velero-cloud-credentials` | `infrastructure/velero/velero/s3` | `cloud` |

Store an AWS shared-credentials file in property `cloud`. Select and configure the S3 provider override separately, including bucket, endpoint, region and AWS plugin. This opt-in alone does not enable backups or create a bucket.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
Apply this opt-in first to create its public bootstrap descriptor. With an
independently authenticated, TLS-verified OpenBao administrator session, provision
its backend from that **rendered** ConfigMap (replace the default namespace below
with the configured NS_VELERO):


```sh
kubectl -n velero get configmap velero-openbao-bootstrap -o jsonpath='{.data.policy\.hcl}' | bao policy write eso-velero-velero -
kubectl -n velero get configmap velero-openbao-bootstrap -o jsonpath='{.data.role\.json}' | bao write auth/kubernetes/role/eso-velero-velero -
```

The policy also permits lookup, renewal and revocation of the authenticated
client's own short-lived token, required for ESO provider validation/lifecycle.
It grants no additional application paths or writes.

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/velero-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.

Live OpenBao/ESO delivery and actual application credential use passed on fresh
K3s. See [runtime findings](../../../../../docs/findings/infra-eso-data-2026-11-01.md).

Namespace placement, service DNS and backend role bindings follow the shared
[namespace mapping](../../../../../docs/operations/namespace-configuration.md). Do not apply raw role.json to OpenBao; it contains namespace placeholders.
