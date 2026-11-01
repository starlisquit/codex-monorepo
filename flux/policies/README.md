# Kyverno policy templates

These are `policies.kyverno.io/v1` **ValidatingPolicy custom resources**, not CRD definitions.
Install the pinned Kyverno engine and its CRDs before reconciling this directory.
The lab's `policies` Flux Kustomization depends on `kyverno`.

All rules start in **Audit** mode with background scanning and scope only to Pods
in `demo` and `applications`. Rules evaluate Pods, including those created by workload controllers. Infrastructure namespaces, storage agents and control-plane workloads
are outside this scope. No mutation or generated resources are configured.

| Policy | Checks |
| --- | --- |
| `platform-container-isolation` | No host network/PID/IPC, no privileged containers, explicit non-root execution |
| `platform-resource-requests` | CPU/memory requests and memory limits for regular and init containers |
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

Evaluation errors use `failurePolicy: Ignore` in these starter templates. Review
policy Ready conditions and errors as well as violation reports. Before enforcing,
consider `Fail` after testing so evaluation failures cannot silently skip checks.
