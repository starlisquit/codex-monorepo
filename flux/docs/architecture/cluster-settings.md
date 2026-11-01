# Cluster-defined settings and reusable Flux wiring

Templates use native Flux post-build substitution. Each cluster owns one
non-secret `flux-system/cluster-settings` ConfigMap, included in its bootstrap
Kustomization. Every selected Flux wiring opt-in reads that ConfigMap through
`spec.postBuild.substituteFrom`; the root Flux Kustomization does too.
No environment-specific manifest generation is needed.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-settings
  namespace: flux-system
  labels:
    reconcile.fluxcd.io/watch: Enabled
data:
  CLUSTER_NAME: production-a
  CA_CERT_NAME: production-root-key
  CA_ISSUER_NAME: production-workload-ca
  CA_BUNDLE_NAME: production-ca
  CA_COMMON_NAME: Production Platform Root CA
  OBSERVABILITY_NAMESPACE: metrics
  CERTIFICATES_NAMESPACE: pki
  OPENBAO_AUTH_ROLE: application-secret-reader
```

Use `${VARIABLE}`, not bare `$VARIABLE`, for Flux substitution. Generic namespace
and capacity defaults use `${OBSERVABILITY_NAMESPACE:=observability}` and
`${STORAGE_CLASS:=ceph-block}`. Root identity settings and application repository/
auth configuration are explicit inputs. All ConfigMap data values are strings.
`CA_CERT_NAME` names the root signing Secret; `CA_BUNDLE_NAME` names the public
trust ConfigMap. It contains no signing key. Credentials remain separate Secrets.

The bootstrap enables `StrictPostBuildSubstitutions`, so missing required values
fail reconciliation instead of silently becoming empty strings. The watch label
triggers reconciliation when settings change. Grafana `${DS_PROMETHEUS}` and
OpenTelemetry `${env:...}` references are escaped as `$${...}` in Git so they
reach the application. Flux's own bootstrap resources opt out of substitution.

## Reusable orchestration

Select `infrastructure/certificates/pki/opt-in/flux` once for the common
cert-manager, root issuer, trust-manager and public Bundle stages. Select operator
wiring once, then the desired application wiring. For example, a cluster root:

```yaml
resources:
- flux-system
- infrastructure.yaml
- ../../infrastructure/certificates/pki/opt-in/flux
- ../../infrastructure/databases/cloudnative-pg/operator/opt-in/flux
- ../../infrastructure/ai/litellm/opt-in/postgresql/flux
- ../../infrastructure/quality/sonarqube/opt-in/postgresql/flux
```

Each DB-enabled profile contains certificate -> database Ready -> integration ->
application stages. Consumers do not repeat that dependency graph or its health
expressions. Other releases expose `opt-in/flux` wiring, including Cilium and the
ClickHouse operator/cluster. Select a full DB-enabled profile instead of also
selecting its basic app wiring; those definitions would own the same Flux stage.

Foundation still selects the needed namespace/source bases exactly once; no
all-namespaces or all-sources bundle is required. The regular validator checks
that every selected release has its namespace/source and readiness coverage.
Ordinary `<release>-cluster-values` ConfigMaps remain available for chart-specific
lists, resources and settings; raw workloads use native Kustomize patches.

The existing `new-validation-run.py` only creates a fresh run folder and bootstrap
skeleton. It requires an explicit Git URL; it does not generate environment
patches or application dependency graphs. GitRepository's bootstrap URL is a
literal cluster-owned value because it must work before Git reconciliation.

## Applying and validating

Post-build substitution happens after `kustomize build`. A raw `kubectl apply -k`
does not substitute environment settings. Use Flux, or render locally with the
same native engine:

```sh
python3 flux/docs/runbooks/scripts/flux_render.py \
  --run flux/clusters/YOUR_RUN \
  --input flux/infrastructure/networking/cilium/values.yaml
```

The renderer uses `flux envsubst --strict`; it does not implement a second
substitution language. Routine validation needs Flux CLI, Kustomize and PyYAML.
`FLUX_BIN` and `KUSTOMIZE_BIN` can point at non-PATH binaries.

Changing a namespace or CA identity after deployment is a migration, not a normal
value edit: review Namespace pruning, PVC ownership, trust overlap and root key
continuity. Existing CA adoption must retain its actual subject/common name via
`CA_COMMON_NAME`; a new display name must not silently replace the trust identity.
