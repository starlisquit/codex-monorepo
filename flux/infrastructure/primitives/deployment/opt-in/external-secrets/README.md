# Deployment: External Secrets environment opt-in

A Kustomize Component that creates an application-specific ServiceAccount,
SecretStore and ExternalSecret, then adds `envFrom.secretRef` to container
`application`. Defaults sync OpenBao KV v2 property `APP_PASSWORD` at
`applications/application/environment` into Secret `application-env`.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: demo
namePrefix: api-
resources:
- ../../../infrastructure/primitives/deployment
components:
- ../../../infrastructure/primitives/deployment/opt-in/external-secrets
labels:
- pairs:
    app.kubernetes.io/name: api
  includeSelectors: true
  includeTemplates: true
patches:
- target:
    kind: ExternalSecret
    name: application-env
  patch: |
    apiVersion: external-secrets.io/v1
    kind: ExternalSecret
    metadata:
      name: application-env
    spec:
      data:
      - secretKey: APP_PASSWORD
        remoteRef:
          key: applications/api/environment
          property: APP_PASSWORD
```

For a wrapper under `flux/clusters/<run>/<app>/`, this produces:

- SecretStore `api-application-openbao`.
- ExternalSecret and owned target Secret `api-application-env`.
- Login service account and OpenBao role `api-application-external-secrets`.

Custom name references keep target Secret, environment reference, store,
service account and role aligned after `namePrefix`/`nameSuffix` transforms.
The ESO controller uses the login account; the application does not use it or
receive its Kubernetes token. No Secret values are stored in the component.

## Backend setup and prerequisites

Install ESO CRDs/controller, initialize/unseal OpenBao, enable KV v2 at `kv` and
Kubernetes auth at `kubernetes`. Distribute public `ConfigMap/platform-ca` into
the app namespace. The store verifies TLS against that bundle. It uses a scoped
TokenRequest with audience `openbao`, not an administrative OpenBao credential.

`policy.hcl` grants read-only access to the default KV path and lifecycle
operations on the authenticated client's own token.
`role.example.json` illustrates binding namespace `demo` and the example's
prefixed service account. Copy and adapt them outside the template for each
application/environment. For the wrapper above change the policy path to
`kv/data/applications/api/environment`, then apply in an independently
authenticated, TLS-verified OpenBao administrator session:

```sh
bao policy write api-application-external-secrets /secure/api-environment-policy.hcl
bao write auth/kubernetes/role/api-application-external-secrets @role.example.json
bao kv put -mount=kv applications/api/environment @/secure/api-environment.json
```

The protected JSON file contains property `APP_PASSWORD`. Add explicit `data`
entries for further environment keys and adjust the policy to the exact paths.
Use globally unique role names/prefixes across namespaces sharing an OpenBao
backend; policy paths and role bindings are not automatically provisioned by
Kustomize or inferred from namespace/name changes.

Gate this composition on ESO/OpenBao readiness. For strict separate credentials
and application Flux stages, put the ServiceAccount, SecretStore and ExternalSecret
from the rendered composition in the credentials stage and gate the Deployment
stage on their readiness. This all-in-one Component does not create that stage
split; a Pod waits for its mandatory Secret until ESO creates it. Require both
ExternalSecret and Deployment health before declaring the composition ready.

ESO refreshes every minute; environment values in running Pods do not update.
Roll the Deployment after coordinated credential changes. `Owner` makes ESO the
sole target Secret owner; do not point it at a CNPG, chart or cert-manager-owned
Secret. Removing the ExternalSecret may delete its owned Secret. Provider deletion
retains the last value but produces a sync failure. See the shared
[application secret contract](../../../../../docs/operations/application-external-secrets.md).

This composes with the injector Component for **different** credentials: ESO
provides environment variables; the injector independently renders files. The
starter echo image does not demonstrate application use of `APP_PASSWORD`.
