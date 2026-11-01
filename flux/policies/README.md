# Policy templates

- [NetworkPolicy templates and live test](network/README.md): opt-in ingress allowlists and an optional namespace baseline.
- [Image registry allowlist](kyverno/image-registries.md): Kyverno policy with Deny enforcement for workload images.
- `kyverno/`: validation policies described below.

## Kyverno

These are `policies.kyverno.io/v1` **ValidatingPolicy custom resources**, not CRD definitions.
Install the pinned Kyverno engine and its CRDs before reconciling this directory.
The lab's `policies` Flux Kustomization depends on `kyverno` and `cilium`.

The isolation, resource-request and image-tag policies start in **Audit** mode
with background scanning. The image repository allowlist uses **Deny/Fail** and
admission-only evaluation. These workload policies scope to Pods in `demo` and
`applications`. Rules evaluate Pods, including those created by workload controllers. Infrastructure namespaces, storage agents and control-plane workloads
are outside this scope. No mutation or generated resources are configured.

| Policy | Checks |
| --- | --- |
| `platform-container-isolation` | No host network/PID/IPC, no privileged containers, explicit non-root execution |
| `platform-resource-requests` | CPU/memory requests and memory limits for regular and init containers |
| `platform-image-registries` | Denies image references outside approved repository prefixes, including init/debug containers |
| `platform-image-tags` | Explicit non-latest tag or sha256 digest; untagged registry-port references are rejected |

Audit reports findings; it does not make insecure Pods secure or deny admission.
Non-latest tags are still mutable. Pin digests where reproducibility is required.
Resource values are checked for presence, not appropriate sizing. Non-root
validation checks declarations, not the image's actual default UID. Explicit `runAsUser: 0` is also reported; these are starter controls,
not a complete Pod Security Standards implementation. No CPU limit is required,
to avoid adding unnecessary throttling to this lab.

## Adopt and verify

```sh
kustomize build flux/policies
kubectl apply --dry-run=server -k flux/policies
flux reconcile kustomization policies --timeout=5m
kubectl get validatingpolicies.policies.kyverno.io
kubectl get policyreports -n demo
kubectl get policyreports -n applications
kubectl get clusterpolicyreports
```

Reports appear after admission/background evaluation; an empty report listing is
not proof every rule passed. Inspect report results and policy controller logs.
Review namespace scope, exceptions and actual findings before changing
`spec.validationActions` to `[Deny]` in a cluster overlay. Test each proposed
enforcement rule with compliant and violating Pods before rollout. Avoid broad
namespace wildcards that accidentally include operators requiring privileges.

Removing these resources with Flux pruning removes the policy definitions; it
neither deletes workloads nor reverses previous admission decisions.

Evaluation errors use `failurePolicy: Ignore` in the Audit starter templates; the
repository allowlist uses `Fail`. Review
policy Ready conditions and errors as well as violation reports. Before enforcing,
consider `Fail` after testing so evaluation failures cannot silently skip checks.

The Audit templates match Pod CREATE/UPDATE, not debug-container subresource admission.
The repository allowlist also matches `pods/ephemeralcontainers` with background
evaluation disabled.
Background scanning can still evaluate saved ephemeral containers for image and
isolation checks. Listing `pods/ephemeralcontainers` as a reporting resource made
the current Kyverno controller request unsupported list/watch permissions and
left policies unready; match the parent Pod instead. Resource budgets exclude
ephemeral containers, whose API does not support resource requests/limits.
