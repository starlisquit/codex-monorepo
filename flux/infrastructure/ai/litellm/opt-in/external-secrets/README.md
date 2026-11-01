# litellm: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `ai`. Store: `litellm-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `litellm-auth` | `infrastructure/ai/litellm/auth` | `master-key`, `salt-key` |
| `litellm-provider-credentials` | `infrastructure/ai/litellm/providers` | `OPENAI_API_KEY` |

Use a strong `sk-` prefixed master key. Keep `salt-key` stable for persisted encrypted credentials; it is required by this opt-in even in database-free mode. Adapt the provider mapping when using another provider.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
With an independently authenticated, TLS-verified OpenBao administrator session,
apply the narrowly scoped backend configuration from this directory:

```sh
bao policy write eso-ai-litellm policy.hcl
bao write auth/kubernetes/role/eso-ai-litellm @role.json
```

The policy also permits lookup, renewal and revocation of the authenticated
client's own short-lived token, required for ESO provider validation/lifecycle.
It grants no additional application paths or writes.

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/litellm-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.

Actual application credential consumption passed on fresh K3s. See
[runtime findings](../../../../../docs/findings/infra-eso-apps-2026-11-01.md).
