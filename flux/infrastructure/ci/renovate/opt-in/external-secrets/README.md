# renovate: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `ci`. Store: `renovate-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `renovate-credentials` | `infrastructure/ci/renovate/credentials` | `RENOVATE_TOKEN` |

Use a dedicated bot token with repository/API permissions scoped to the selected repositories. The next CronJob receives updates; an already running Job keeps its environment.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
With an independently authenticated, TLS-verified OpenBao administrator session,
apply the narrowly scoped backend configuration from this directory:

```sh
bao policy write eso-ci-renovate policy.hcl
bao write auth/kubernetes/role/eso-ci-renovate @role.json
```

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/renovate-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.
