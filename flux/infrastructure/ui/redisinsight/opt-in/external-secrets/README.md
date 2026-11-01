# redisinsight: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `ui`. Store: `redisinsight-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `redisinsight-encryption` | `infrastructure/ui/redisinsight/encryption` | `key` |

Keep the encryption key stable and backed up independently. Changing it can make existing saved credentials unreadable; this is not an automatically rotatable password.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
With an independently authenticated, TLS-verified OpenBao administrator session,
apply the narrowly scoped backend configuration from this directory:

```sh
bao policy write eso-ui-redisinsight policy.hcl
bao write auth/kubernetes/role/eso-ui-redisinsight @role.json
```

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/redisinsight-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.
