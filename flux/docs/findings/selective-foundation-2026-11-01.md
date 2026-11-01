# Selective namespaces and Flux sources — 2026-11-01

Namespaces and sources are now independently selectable Kustomize bases. Neither
all-in-one bundle is required. Definitions remain centralized; workload folders
do not regain private namespace.yaml files or source copies.

## Layout and selection

- Each namespace has a base at `infrastructure/namespaces/<name>`, with its
  Namespace in resource.yaml and a Kustomization. All 18 definitions retain
  their prior names and labels, including the security namespace policies.
- Each Flux source has a base at `infrastructure/sources/<metadata.name>`, with
  its original HelmRepository or OCIRepository in resource.yaml. All 26 source
  definitions retain their URLs, version pins, names and flux-system namespace.
- The root namespaces and sources Kustomizations remain backward-compatible,
  optional convenience bundles. Consumers choose the per-resource bases when
  they do not want every namespace or source.
- The full-platform foundation now explicitly selects its 14 used namespaces
  and 20 referenced sources. It no longer selects unused ai, ci, proxy or
  quality namespaces, or gitlab, nats-nui, nginx, renovate, sonarqube and litellm
  sources. Applications is retained because selected policies target it.
- The minimal Cilium lab selects the shared Cilium source base instead of
  maintaining its own source copy. It still uses existing kube-system.

A small deployment wrapper can use:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
- ../../../infrastructure/namespaces/ai
- ../../../infrastructure/sources/litellm
- ../../../infrastructure/ai/litellm
```

Provision the template's actual credential Secrets separately. Select shared
namespaces and sources once when multiple releases use them. This keeps one
intended reconciliation owner and avoids duplicate identities when composing
multiple templates. Do not add an outer namespace transformer that relocates
flux-system sources into an application namespace.

## Why createNamespace alone is insufficient here

The native Flux flag is `spec.install.createNamespace`. It controls creation
of Helm's target namespace during installation. These templates already store
the HelmRelease and values ConfigMap in the application namespace; that namespace
must exist before Helm can reconcile their release. The flag does not create
Flux sources and does not manage Pod Security labels on namespace objects.

A different architecture could store HelmReleases/values in an existing control
namespace and set a distinct targetNamespace with createNamespace enabled. That
would change release identities, values-reference locations, health checks and
dependencies across this repository. This change does not perform that migration;
it retains current identities and exposes small native Kustomize prerequisites.

## Verification and deployment impact

- All **148 Kustomize builds** passed, including every individual namespace and
  source base, default templates and both Cilium bootstrap consumers.
- Existing 37 selected Flux child definitions and all 25 HelmRelease readiness
  coverage checks still pass. Workload deployment dependencies were unchanged.
- Compared before/after selected manifests: 146 unique identities became 136.
  The only removed desired identities are the four unused namespaces and six
  unused sources listed above. Every retained object is unchanged.
- Verified all 31 shared HelmReleases have independently selectable source and
  namespace prerequisites, except the existing bootstrap-owned system namespaces.
- Built a minimal LiteLLM wrapper and asserted exactly Namespace/ai, the LiteLLM
  OCI source and the LiteLLM release, without unrelated namespaces or sources.
- Built a GitLab Runner + Renovate wrapper and asserted a single shared ci
  namespace, exactly their two source objects and two releases.
- Compared both optional bulk bundles with the previous commit: their rendered
  resources are identical. Existing consumers may still opt into the bundles.
- Compared the minimal Cilium overlay with its previous committed version:
  rendered resources are identical despite removing its private source copy.
- Updated template instructions and stale namespace-creation claims, including
  source paths and Velero's namespace provisioning command. Whitespace passed.

See [sanitized comparison evidence](evidence/selective-foundation-2026-11-01.json).
No live deployment, namespace deletion, ownership transfer or pruning was run.
For already-running clusters, review foundation pruning before applying a
reduced namespace selection: a namespace absent from desired Git resources can
still contain independently installed workloads or data. Verify actual usage
and deliberate retention before allowing a previous namespace owner to prune.
This is an existing-resource migration concern, not a prerequisite for selecting
only the needed bases in a new cluster.
