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
application. Credentials can reference existing Secrets or use the credential opt-ins below.
The base primitive creates no namespace, source, credential, ingress, storage or RBAC objects. If API access
is required, select a dedicated ServiceAccount and scoped permissions explicitly.

In Flux, reconcile the namespace first and health-check the resulting Deployment
(or use `wait: true`). Optional Service selects the Deployment over its named
HTTP port. No traffic is exposed outside the cluster.

## Monitoring opt-ins

Keep workload-specific scrape definitions here; monitoring CRDs, operators and
collectors belong under `infrastructure/observability`.

- [`opt-in/podmonitor`](opt-in/podmonitor): scrape the Pods directly; no Service
  required.
- [`opt-in/servicemonitor`](opt-in/servicemonitor): scrape through an included,
  dedicated internal metrics Service; the HTTP Service opt-in is independent.

Both add a named `metrics` container port (8081) and default to `/metrics`, 30s
interval and 10s timeout. They select targets in the consuming namespace, and
custom Kustomize selector mappings keep them aligned with consumer label changes.
Normally choose one monitor per workload. The app must serve Prometheus metrics;
the starter HTTP echo image does not. Select monitoring CRDs and a collector
separately, and gate these resources on CRD readiness in Flux. See each component's
README for composition examples and collection prerequisites.

Validation: repository Kustomize builds and a two-application composition check
cover object names, namespace transforms and selector isolation, including the
optional Service. The primitive was also deployed with a Python protocol fixture, verifying
readiness, rollout, non-root execution, read-only root filesystem and no mounted
API token. The default starter image itself was not exercised.

See [native Gateway API runtime findings](../../../docs/findings/primitives-cilium-2026-11-01.md)
for the exact versions, fixture changes, assertions and limits.

## Credential opt-ins

- [`opt-in/external-secrets`](opt-in/external-secrets/README.md): scoped OpenBao
  SecretStore and ExternalSecret, consumed as application environment variables.
- [`opt-in/openbao-injector`](opt-in/openbao-injector/README.md): dedicated workload
  identity, projected login token and agent annotations for file-based credentials.

Both are Components selected through `components:` and support prefixed application
wrappers. Choose one delivery method, or combine them for distinct credentials.
Configure scoped OpenBao policies/roles and populate KV separately; example backend
files are supplied, but Kustomize does not apply them to OpenBao. Neither integration
manages PKI or operator-generated secrets. See each README for trust, readiness,
name/path customization and refresh behavior. Both passed focused K3s runtime verification on parallel fresh clusters:
[External Secrets](../../../docs/findings/deployment-external-secrets-runtime-2026-11-01.md)
and [OpenBao injector](../../../docs/findings/deployment-injector-runtime-2026-11-01.md).
Checks cover real application consumption, scoped authentication, refresh behavior
and failure handling. Routine validation also checks all combinations with the
other Deployment opt-ins.
