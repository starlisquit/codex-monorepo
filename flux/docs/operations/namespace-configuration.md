# Configure namespaces once per cluster

Namespace settings are Flux post-build variables, not application environment
variables. Shared templates use `${NS_AI}`, `${NS_SECRETS}` and the other declared
namespace-group variables. No domains, credentials, issuer names, service names
or OpenBao KV paths are made configurable through this mechanism.

## Consumer end result

New runs created by `new-validation-run.py` already include the map bootstrap,
strict Flux substitutions and propagation to root/child Kustomizations. Edit only
`flux/clusters/<run>/flux-system/namespace-overrides.yaml` for changed groups:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-namespaces
  namespace: flux-system
# Omitted keys retain the shared defaults.
data:
  NS_AI: platform-ai
  NS_SECRETS: platform-secrets
  NS_CERTIFICATES: platform-certificates
  NS_DATABASES: platform-databases
  NS_OBSERVABILITY: platform-observability
```

The [shared defaults](../../bootstrap/namespace-config/configmap.yaml) retain all
18 existing namespace groups. Entries in this ConfigMap do not create namespaces
or install workloads/sources. Select only required namespace/source bases in the
foundation. Members of one group move together (for example Runner/Renovate use
NS_CI); independent placement within a group requires a separately scoped consumer
configuration and matching readiness/backend references. Per-application namespace
variables and namespace consolidation are not part of this initial contract.

Mappings must use valid DNS-label namespace names and remain distinct. `flux-system`
and `kube-system` stay bootstrap-owned and are not configurable. Do not combine a
separate Kustomize `namespace:` override with inconsistent group variables: the
mapping is the authoritative value for parameterized infrastructure templates.

For a new run, select namespaces/sources normally and set the branch explicitly
when testing an unmerged feature:

```sh
python3 flux/docs/runbooks/scripts/new-validation-run.py \
  --name namespace-validation --play-id ACTUAL_PLAY_ID \
  --namespace ai --namespace secrets --namespace certificates \
  --source litellm --source openbao --source external-secrets \
  --git-ref YOUR_BRANCH
```

Namespace/source selection does not assemble an entire workload dependency DAG;
add the required stages and readiness gates as before. The checked-in namespace
validation runs demonstrate a complete focused graph. Existing retained runs are
historical snapshots at their recorded revisions; never reuse one for a new play.

## Existing consumer adoption

For a current consumer, first keep the default names. Add the namespace-config
base and Flux substitution Component to its bootstrap/root wiring as shown in
the generated validation folders, and create the map before enabling consumers.
Apply the common Component at the level that defines child Flux Kustomizations,
not only inside a workload. Enable strict controller substitution and preserve
native application expressions before switching to these parameterized templates.
The default-profile comparison preserves existing workload objects; adding the
mapping does not itself require moving them. Prior report run folders remain
historical records, not an automatic migration recipe.

## What follows the mapping

The variables cover namespace objects/metadata, Helm value ConfigMaps, release
dependencies, cross-namespace references, service DNS and certificate DNS SANs,
CA-injection references, trust-manager source/target namespaces, and relevant
namespace selectors in policies. Charts still use native `.Release.Namespace`
where they already support it. Names and credential addresses remain stable.

The same source is attached to every generated Flux Kustomization:

```yaml
spec:
  postBuild:
    substituteFrom:
    - kind: ConfigMap
      name: cluster-namespaces
```

The ConfigMap is bootstrapped in `flux-system` before root reconciliation; it is
not created by a stage that needs its own values first. The root resolves child
health-check namespaces, and children resolve their own selected resources.
Substitution is not inherited automatically; the reusable
[Flux wiring Component](../../bootstrap/namespace-config/opt-in/flux-substitution/kustomization.yaml)
applies it to both levels. It owns `spec.postBuild`; do not layer unrelated
postBuild configuration over it without deliberately merging the contract.

The bootstrap enables `StrictPostBuildSubstitutions=true` on kustomize-controller.
Missing variables fail reconciliation instead of silently producing empty names.
The map is Flux-watched; change its Git-owned override file rather than editing
the live ConfigMap and expecting that edit to survive Git reconciliation.

## OpenBao backend roles follow the same mapping

Each infrastructure application credential opt-in now creates a **non-secret**
`<store-name>-bootstrap` ConfigMap containing `role.json` and `policy.hcl`. Flux
substitutes namespace bindings in that JSON before storing it. These descriptors
contain no application passwords, JWTs or administrator credentials.

After OpenBao is initialized/unsealed, apply the credential opt-in to create its
descriptor, store, service account and ExternalSecrets. Before waiting for store
readiness, an independently authenticated, TLS-verified OpenBao administrator
provisions the backend using the rendered data. For LiteLLM with NS_AI=platform-ai:

```sh
kubectl -n platform-ai get configmap litellm-openbao-bootstrap \
  -o jsonpath='{.data.policy\.hcl}' | bao policy write eso-ai-litellm -
kubectl -n platform-ai get configmap litellm-openbao-bootstrap \
  -o jsonpath='{.data.role\.json}' | bao write auth/kubernetes/role/eso-ai-litellm -
```

Populate the documented KV values securely, then require SecretStore and
ExternalSecret readiness before the application. Flux creates the descriptors;
it does not automatically authenticate as an OpenBao administrator or configure
backend roles. Do not apply the raw role.json from disk now that it contains
namespace placeholders. KV paths and role names stay stable; changing application
placement does not migrate provider data or expand its allowed paths.

Deployment primitive role.example.json files remain illustrative administrative
examples for arbitrary consumer workloads; adapt their account/namespace bindings
to that workload. The generated descriptors cover the nine infrastructure
application credential integrations.

## Preserve other interpolation syntaxes

Native Flux substitution recognizes `${NAME}`, not bare `$NAME`. It would also
process application expressions. Source templates therefore escape literal
Grafana/OpenTelemetry expressions as `$${DS_PROMETHEUS}` and
`$${env:MY_POD_IP}`; they become the original `${...}` after one substitution pass.
`$(DATABASE_PASSWORD)` and other Kubernetes/shell `$()` expressions remain intact.
Vendored CRDs have substitution disabled because their schema descriptions
contain illustrative expressions; they contain no configurable namespace fields.
Never run a second envsubst pass over the already-rendered objects.

Plain `kustomize build` now displays namespace placeholders. It is an inspection
step, not ready-to-apply output. Flux performs the post-build step during deployment.
For local rendering/validation with installed Flux/Kustomize:

```sh
KUSTOMIZE_BIN=kustomize FLUX_BIN=flux \
  python3 flux/docs/runbooks/scripts/namespace_support.py \
  flux/infrastructure/ai/litellm
```

This helper uses the native strict Flux CLI, not a separate templating engine.
By default it uses the shared mapping; set NAMESPACE_PROFILE to a ConfigMap-shaped
YAML file containing namespace overrides to inspect a custom profile. Direct Helm
CLI lint/install commands must likewise receive rendered values, not raw namespace
placeholders. These mappings contain no credentials and do not require Secrets.

## Validation and migration boundary

`validate.sh` requires Flux and Kustomize. It checks default/custom shared-base
renders, all Component compositions and application Secret contracts in both
profiles, rendered OpenBao role bindings, DNS/SAN namespace references, generated
root/child wiring, literal application expressions, and invalid/missing mappings.
The branch's findings record the focused live default/custom K3s results.

Changing an existing namespace is a migration, not a rename. It creates new
resources, may change service identities/SANs and OpenBao bindings, and does not
move PVC data. NS_CERTIFICATES also controls signing-Secret location: moving an
existing PKI without migrating that material can create a different root. Preserve
signing identity deliberately rather than treating the map edit as CA migration.
Plan data transfer, certificate/client changes and old-resource
pruning explicitly. The initial defaults preserve current placement; editing the
map does not make a stateful namespace move automatic.

[Default/custom live verification and scope](../findings/namespace-configuration-2026-11-02.md)
records actual application, PKI, role-binding and strict-controller results.
