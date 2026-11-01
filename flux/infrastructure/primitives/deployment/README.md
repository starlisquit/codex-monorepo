# Deployment primitive

Native `apps/v1` Deployment for a stateless HTTP application. Defaults include
two replicas, rolling updates without unavailable replicas, bounded revision
history, resources, startup/readiness/liveness probes, non-root execution,
a read-only root filesystem and no mounted Kubernetes API token.

The pinned `hashicorp/http-echo:1.0.0` image is a starter application on port 8080.
It is not a production application. Replace image, arguments, ports, probes and
resources together. Add writable volumes if required instead of disabling the
read-only filesystem without checking the application's needs. The extra rolling
update pod requires spare scheduling capacity. Two replicas alone do not provide
node failure tolerance; configure placement for your environment.

## Consume from a cluster wrapper

For a wrapper at `flux/clusters/<run>/my-app/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: demo
namePrefix: api-
resources:
- ../../../infrastructure/primitives/deployment
components:
- ../../../infrastructure/primitives/deployment/opt-in/service
labels:
- pairs:
    app.kubernetes.io/name: api
  includeSelectors: true
  includeTemplates: true
```

Select `infrastructure/namespaces/demo` separately, or provision your own
namespace. This produces Deployment and ClusterIP Service `api-application`,
with matching `api` selectors and pod labels. Omit `components` for a worker
without a Service. Each application needs its own wrapper, unique name prefix
and unique selector label; a name prefix alone does not isolate selectors.
Selectors are immutable after creation, so keep them stable for deployed apps.

Use native `images`, `replicas` and `patches` in the wrapper to configure the
application. Credentials must reference existing Secrets. This primitive creates
no namespace, source, credential, ingress, storage or RBAC objects. If API access
is required, select a dedicated ServiceAccount and scoped permissions explicitly.

In Flux, reconcile the namespace first and health-check the resulting Deployment
(or use `wait: true`). Optional Service selects the Deployment over its named
HTTP port. No traffic is exposed outside the cluster.

Validation: repository Kustomize builds and a two-application composition check
cover object names, namespace transforms and selector isolation, including the
optional Service. The primitive was also deployed with a Python protocol fixture, verifying
readiness, rollout, non-root execution, read-only root filesystem and no mounted
API token. The default starter image itself was not exercised.

See [native Gateway API runtime findings](../../../docs/findings/primitives-cilium-2026-11-01.md)
for the exact versions, fixture changes, assertions and limits.
