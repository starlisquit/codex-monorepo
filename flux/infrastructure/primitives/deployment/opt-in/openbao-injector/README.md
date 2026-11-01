# Deployment: OpenBao agent injector opt-in

A Kustomize Component that creates a dedicated workload ServiceAccount and adds
OpenBao agent injection annotations to the Deployment's Pod template. The shared
OpenBao chart uses HashiCorp's compatible `vault-k8s:1.7.6` injector, so annotations
intentionally use `vault.hashicorp.com`, not an invented OpenBao annotation prefix.

The injector adds an init agent and a continuing agent sidecar. They authenticate
to OpenBao using the Pod's service account and render KV v2 data to the shared
memory-backed file `/vault/secrets/config.json`. This method creates **no
application Kubernetes Secret** and does not turn file contents into environment
variables. The application must read the JSON file and support reload if needed.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: demo
namePrefix: api-
resources:
- ../../../infrastructure/primitives/deployment
components:
- ../../../infrastructure/primitives/deployment/opt-in/openbao-injector
labels:
- pairs:
    app.kubernetes.io/name: api
  includeSelectors: true
  includeTemplates: true
patches:
- target:
    kind: Deployment
    name: application
  patch: |
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: application
    spec:
      template:
        metadata:
          annotations:
            vault.hashicorp.com/agent-inject-secret-config.json: kv/data/applications/api/files
            vault.hashicorp.com/agent-inject-template-config.json: |
              {{- with secret "kv/data/applications/api/files" -}}
              {{ .Data.data | toJSON }}
              {{- end -}}
```

For a wrapper under `flux/clusters/<run>/<app>/`, the workload service account
and OpenBao role become `api-application-openbao-injector`. A custom name-reference
mapping keeps the role annotation aligned with the renamed account. Namespace
transforms affect the account/Deployment; backend role bindings and KV paths must
be configured explicitly. Use role names/prefixes unique across namespaces sharing
the backend. The default path is `kv/data/applications/application/files`; update
both the secret annotation and embedded template when changing it.

## Identity and trust

Automatic API-token mounting remains disabled. A dedicated projected token volume
has audience `openbao` and lifetime 600 seconds. The injector's supported
`agent-service-account-token-volume-name` annotation mounts it into its agents;
the application container does not mount it. No RBAC grants or root tokens are
added. The injector does not expose its OpenBao token to the app.

Agent UID/GID are 10001, matching the primitive. The rendered file has permissions
0400. Update agent UID/GID together with application identity when customizing.
The auth token is read-only 0444 inside the agents' private mount so the non-root
agent can read it; it is not mounted into the app.

TLS verification is enabled. The shared OpenBao HelmRelease already supplies the
public server CA bytes through `AGENT_INJECT_VAULT_CACERT_BYTES`. This Component
relies on that injector configuration; it does not mount server private keys or
change PKI ownership. Install a healthy injector with its centrally signed webhook
certificate and trusted webhook CA before creating these Pods. If deploying a
different injector, configure trusted CA bytes or a verified CA-file mount rather
than disabling TLS verification. Refresh injector configuration when its trust
bundle changes and verify how existing agents receive that change.

## Backend setup and operation

`policy.hcl` grants read access to the default file KV path and lifecycle
operations on the agent's own token (lookup, renewal and revocation).
`role.example.json` binds the example's prefixed account in namespace `demo`,
requires audience `openbao` and assigns a short-lived scoped policy. Adapt a
policy copy to `kv/data/applications/api/files` for the wrapper above, then apply
with an independently authenticated, TLS-verified OpenBao administrator session:

```sh
bao policy write api-application-openbao-injector /secure/api-files-policy.hcl
bao write auth/kubernetes/role/api-application-openbao-injector @role.example.json
bao kv put -mount=kv applications/api/files @/secure/api-files.json
```

The files hold no credentials in Git. OpenBao must already be initialized/unsealed,
with Kubernetes auth and TokenReview permissions configured. Application namespace,
network access and injector admission readiness are cluster prerequisites.

An init-agent authentication/render failure blocks application startup after
successful injection. Admission failure behavior is controlled by the injector's
webhook configuration; an injector configured to fail open can admit an unmutated
Pod. Use a fail-closed webhook where required, verify actual injected containers,
and make the real application fail startup if its required file is absent.
The starter echo image does not read this file or implement that check.

The continuing agent can refresh rendered data, but the application must reload
it; neither this Component nor ESO rotates upstream credentials. Budget resources
for both injected containers. Do not render untrusted values as executable shell
exports; the default renders JSON using `toJSON` to preserve escaping.

This composes with `external-secrets` for distinct file and environment secrets.
The workload's service account remains independent of ESO's login account. No
PKI, CNPG or other controller-managed Secret is claimed.
