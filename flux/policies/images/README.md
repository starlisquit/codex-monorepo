# Enforced image repository allowlist

This uses Kubernetes' built-in `admissionregistration.k8s.io/v1`
ValidatingAdmissionPolicy and Binding (Kubernetes 1.30+), not a Kyverno CRD.
It is included in `flux/policies`; its binding uses **Deny** and the policy uses
**Fail** on evaluation errors. The other Kyverno templates remain Audit-only.

Scope: Pod creation/update in namespaces `demo` and `applications`, including
`pods/ephemeralcontainers` updates. Regular, init and ephemeral container images
must start with one of these exact repository prefixes:

- `ghcr.io/open-telemetry/`
- `docker.io/library/`
- `docker.io/otel/`

Edit `spec.variables[name=allowedPrefixes].expression` and the validation message
for your own registries. A private example is `registry.example.com/team/`, or
`registry.example.com:5000/team/` when that port is part of the image reference.
These are repository namespace boundaries, not merely broad public-registry
host allowlists. The trailing slash prevents lookalike hostname/path matches.

Fully qualify image references: use `docker.io/library/busybox:1.37.0`, not
`busybox:1.37.0` or `library/busybox:1.37.0`. The demo Collector repository and
severity fixture are qualified accordingly. Approved registries do not establish
image authenticity: this policy does not verify signatures, digests, vulnerability
status, or repository-owner permissions. Tag restrictions remain a separate policy.

This is admission enforcement, not a firewall on kubelet registry traffic. Cached
images still need an approved reference on new Pods. Existing Pods are not evicted
or retrospectively scanned. A denied controller-created Pod appears as a failed
Pod creation event; its Deployment object can still be accepted. User RBAC must
prevent changing the policy/binding or creating workloads in excluded namespaces.
Infrastructure namespaces are deliberately outside this template's scope.

## Validate and adopt

```sh
kustomize build flux/policies/images
kubectl apply --dry-run=server -k flux/policies/images
kubectl apply -k flux/policies/images
kubectl get validatingadmissionpolicy platform-image-registries -o yaml
kubectl get validatingadmissionpolicybinding platform-image-registries
```

Inspect `status.typeChecking.expressionWarnings` and policy conditions. On a live
cluster, check both admission outcomes with server-side dry runs:

```sh
kubectl -n applications run image-allow-check --image=docker.io/library/busybox:1.37.0 --restart=Never --dry-run=server -o yaml
# Expected rejection:
kubectl -n applications run image-deny-check --image=unapproved.example/team/app:1 --restart=Never --dry-run=server -o yaml
```

Also test init-container and `kubectl debug --dry-run=server` (where supported)
subresource paths using an existing test Pod. The isolated CEL tests under
`tests/` exercise the actual expressions with allowed/denied references and all
container types. They do not replace Kubernetes admission/API integration checks.
The last playground was destroyed, so no live policy activation is claimed.

Run the expression tests with Go 1.23+:

```sh
cd flux/policies/images/tests
go test -v ./...
```

The test loads the policy YAML rather than copying the CEL expression into a
separate implementation. Module versions and checksums are pinned in this folder.
