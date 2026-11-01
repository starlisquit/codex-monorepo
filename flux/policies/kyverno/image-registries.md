# Image repository allowlist

`image-registries.yaml` is a Kyverno `policies.kyverno.io/v1` ValidatingPolicy,
included by this directory's Kustomization. It uses **Deny** with **Fail** on
evaluation errors, unlike the Audit-only starter policies alongside it.
Kubernetes VAP autogeneration is disabled: Kyverno handles admission directly.

Scope: Pod CREATE/UPDATE in `demo` and `applications`, including updates through
`pods/ephemeralcontainers`. Regular, init and ephemeral container images must use
fully qualified references starting with one of these exact prefixes:

- `ghcr.io/open-telemetry/`
- `docker.io/library/`
- `docker.io/otel/`

Edit `spec.variables[name=allowedPrefixes].expression` and the rejection message
for your registry/repository namespaces. Keep the trailing slash to exclude
lookalike hostnames and repository prefixes. Short names such as `busybox:1.37.0`
are rejected; use `docker.io/library/busybox:1.37.0` instead. The demo Collector
and severity fixture already use qualified references.

Background evaluation is disabled because this policy includes admission-only
subresource requests. Existing Pods are not retrospectively scanned or evicted.
An accepted Deployment can still fail to create its Pods when an image is denied.
This restricts image references, not kubelet network egress, registry mirrors,
signatures or CVE status. Protect excluded namespaces and policy modification
through RBAC. Image-tag checks remain a separate policy.

```sh
kustomize build flux/policies/kyverno
kubectl apply --dry-run=server -f flux/policies/kyverno/image-registries.yaml
kubectl get validatingpolicy.policies.kyverno.io platform-image-registries -o yaml
```

On the next cluster, inspect policy Ready/webhook/RBAC conditions and perform
allowed/denied server-side dry runs, including init and debug-container requests.
There is no running playground, so live admission is not claimed here. The former
built-in Kubernetes VAP/binding manifests and image-policy test files were removed.
For an existing installation that requires continuous enforcement, confirm the
Kyverno policy is Ready before retiring the old binding; normal Flux pruning will
remove the old native resources once their manifests are removed from Git.
