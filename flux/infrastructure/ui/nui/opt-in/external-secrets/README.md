# nui: OpenBao credentials opt-in

Select this directory as a **resource** in a cluster-owned credentials stage.
It is a standalone Kustomization, not a Component; selecting the application
alone does not enable it. Namespace: `broker`. Store: `nui-openbao`.

| Kubernetes Secret | OpenBao KV v2 key (under `kv`) | Required properties |
|---|---|---|
| `nui-contexts` | `infrastructure/broker/nui/contexts` | `platform.json` |

Store the complete NATS CLI context JSON in `platform.json`. The document can contain connection credentials; keep it out of Git. This opt-in does not own broker credentials or TLS keys. If file credentials are required, supply `nui-creds` and `credsVolume.items` separately; this opt-in covers inline-context credentials only.

Read the [shared setup, ownership and rotation contract](../../../../../docs/operations/application-external-secrets.md) first.
With an independently authenticated, TLS-verified OpenBao administrator session,
apply the narrowly scoped backend configuration from this directory:

```sh
bao policy write eso-broker-nui policy.hcl
bao write auth/kubernetes/role/eso-broker-nui @role.json
```

The policy also permits lookup, renewal and revocation of the authenticated
client's own short-lived token, required for ESO provider validation/lifecycle.
It grants no additional application paths or writes.

These files contain no credential values. Populate the listed KV keys through
your secure administrative workflow before deployment. Paths are relative to
the KV mount; policies intentionally use the API's `kv/data/` prefix. Override
store endpoint/mount/role and policy paths together when isolating environments.

Wait for `SecretStore/nui-openbao` and each ExternalSecret to report `Ready=True`
before reconciling the application. No certificates, root/unseal material or
operator-generated passwords are managed by this opt-in.

Live OpenBao/ESO delivery and actual application credential use passed on a fresh
K3s run. See [runtime findings](../../../../../docs/findings/infra-eso-ui-2026-11-01.md).
