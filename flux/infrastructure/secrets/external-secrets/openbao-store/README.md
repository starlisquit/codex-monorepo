# External Secrets with OpenBao

Reusable, opt-in integration: a ServiceAccount for ESO token requests and a
namespaced SecretStore using the platform OpenBao HTTPS endpoint and trusted CA.
The parent External Secrets chart directory does not include this directory:
these CRs must reconcile after the ESO CRDs/webhook and OpenBao are ready.

A cluster wrapper only needs:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- ../../../infrastructure/secrets/external-secrets/openbao-store
```

Use a separate Flux Kustomization with dependsOn gates for `external-secrets`
and `openbao`, and check the SecretStore Ready condition. The names in those
Flux gates refer to the consuming cluster's orchestration, not HelmRelease
names. Ensure the `secrets` namespace exists first.

OpenBao's official chart owns the `system:auth-delegator` binding. The shared
OpenBao values explicitly enable `server.authDelegator.enabled`. With the
standard release/namespace its binding is `secrets-openbao-server-binding` for
ServiceAccount `secrets/openbao`. Do not duplicate that binding in a cluster.

The store preserves the existing platform contract: KV v2 mount `kv`, auth
mount `kubernetes`, role `external-secrets-lab`, ServiceAccount
`external-secrets-openbao`, audience `openbao`, and CA Secret
`openbao-server-tls` key `ca.crt`. The role's legacy lab name is retained to avoid
breaking initialized backends; it is not an automatically provisioned policy.
Change the store fields when selecting a different namespace, endpoint, role,
mount or CA. Those are actual deployment-specific settings, not boilerplate.

OpenBao initialization, unsealing, Kubernetes auth configuration and policy/role
creation remain backend operations. Installing these Kubernetes resources does
not perform them. The lab helper in `runbooks/scripts/configure-openbao.py`
creates a role scoped to `kv/data/lab/*`, bound to this service account,
namespace and audience. Create appropriately scoped roles for production;
no administrator token is embedded in the SecretStore.

`verification/` is separately selectable and creates only the non-sensitive
lab ExternalSecret `openbao-verification`. It requires the marker at
`lab/verification`, property `status`, provisioned by the lab helper. Select it
alongside this integration for a smoke test; ordinary consumers should omit it.
The existing iximiuz overlay selects both directories and retains its health
checks and dependency order.

The former custom binding `openbao-token-review` is no longer desired. Because
the existing secret-store Flux Kustomization has prune disabled, that redundant
binding may remain in an already-running cluster. It does not need to be copied
into new clusters. Remove the old binding only after confirming the official
chart-owned binding grants the expected server account TokenReview permissions.
