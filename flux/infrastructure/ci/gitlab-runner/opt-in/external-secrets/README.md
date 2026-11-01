# gitlab-runner: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `ci`. Store: `gitlab-runner-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `gitlab-runner-auth` | `infrastructure/ci/gitlab-runner/auth` | `runner-token` |

Store a current GitLab runner authentication token, not a legacy registration token. The template supplies the required empty `runner-registration-token` key. Token minting/rotation in GitLab remains an administrative operation.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
Apply this opt-in first to create its public bootstrap descriptor. With an
independently authenticated, TLS-verified OpenBao administrator session, provision
its backend from that **rendered** ConfigMap (replace the default namespace below
with the configured NS_CI):


```sh
kubectl -n ci get configmap gitlab-runner-openbao-bootstrap -o jsonpath='{.data.policy\.hcl}' | bao policy write eso-ci-gitlab-runner -
kubectl -n ci get configmap gitlab-runner-openbao-bootstrap -o jsonpath='{.data.role\.json}' | bao write auth/kubernetes/role/eso-ci-gitlab-runner -
```

The policy also permits lookup, renewal and revocation of the authenticated
client's own short-lived token, required for ESO provider validation/lifecycle.
It grants no additional application paths or writes.

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/gitlab-runner-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.

Live OpenBao/ESO delivery and actual application credential use passed on a fresh
K3s run. See [runtime findings](../../../../../docs/findings/infra-eso-ci-2026-11-01.md).

Namespace placement, service DNS and backend role bindings follow the shared
[namespace mapping](../../../../../docs/operations/namespace-configuration.md). Do not apply raw role.json to OpenBao; it contains namespace placeholders.
