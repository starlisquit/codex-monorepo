# Reusable infrastructure versus cluster configuration — 2026-11-01

> Layout and namespace ownership were subsequently consolidated; see
> [the layout refactor](template-layout-2026-11-01.md). Historical validation results below remain unchanged.

## Changes made

The cluster overlays no longer repeat standard Helm reconciliation settings or
copy the OpenBao store resources. Deployment selection and actual environmental
configuration remain in the cluster. This was an offline manifest refactor;
no new playground or live cluster mutation was needed or performed.

| Finding | Shared location / resulting behavior |
| --- | --- |
| Repeated suspend:false and timeout patches | Removed 49 overlay fields/JSON-patch operations. All 31 shared HelmReleases have explicit timeouts: 15m normally, existing 5m behavior retained for Cilium and metrics-server. Added defaults to 23 releases that lacked them. Selecting a release enables reconciliation without an activation patch. |
| ESO ServiceAccount and OpenBao SecretStore defined in a cluster | Moved to infrastructure/secrets/external-secrets/opt-in/openbao-store; select after ESO and OpenBao are ready. |
| Duplicate token-review ClusterRoleBinding | Removed the custom openbao-token-review from desired resources. Official OpenBao chart 0.30.6 already grants the same server account system:auth-delegator via secrets-openbao-server-binding. Explicitly enabled server.authDelegator.enabled in shared values. |
| Verification ExternalSecret coupled to ordinary integration | Moved to the separately selectable external-secrets/opt-in/openbao-verification subdirectory. Existing lab selects it; ordinary deployments need not provision lab/verification. |
| Shared namespace declarations copied into foundation | Moved intact to infrastructure/namespaces; foundation selects the bundle. Smaller clusters can still provision their own subset. |
| Duplicate Cilium HelmRepository plus deletion patch | Full-platform foundation now selects the existing shared source. Removed its exclusion patch and the full-platform Cilium source copy. The minimal iximiuz-labs overlay keeps its source because it does not deploy that foundation. |
| Stable PostgreSQL TLS references in cluster patch | Moved to the shared application PostgreSQL template. Cluster retains its 1Gi storage override; prerequisites are documented alongside the template. |
| Gateway API CRDs stored in cluster overlay | Moved unchanged to infrastructure/networking/gateway-api-crds, including upstream notices and Standard channel v1.4.0 annotations. Existing CRD health gate stays in place. |
| Generic Ceph write/sync/read Job and PVC stored in cluster overlay | Moved unchanged to separately selectable infrastructure/storage/rook-ceph/cluster/opt-in/verification. Existing storage-ready dependency gate still selects and waits for it. |

A simple component wrapper, such as blackbox, now consists only of its
Kustomization API/kind and the shared infrastructure resource path. The store
wrapper likewise selects the shared integration and optional verification
subdirectory rather than redefining ServiceAccount, RBAC, SecretStore or
ExternalSecret objects.

## OpenBao integration contract

The shared store retains the existing service account, TLS endpoint, CA,
KV v2 mount, Kubernetes auth mount and audience. The role name
external-secrets-lab is preserved for compatibility with already-initialized
backends and the current scoped bootstrap helper. It does not imply broad
access: the helper's policy only permits the lab prefix. Different backend
roles, paths, endpoints, namespaces and CAs are legitimate deployment-specific
settings and should be configured for that installation.

The store component deliberately is not included in the ESO HelmRelease's own
directory. A SecretStore requires the ESO CRDs/webhook and a ready, initialized
OpenBao backend. The existing secret-store Flux Kustomization keeps its
dependsOn entries for external-secrets and openbao, and its SecretStore and
verification ExternalSecret health checks. Moving resources does not eliminate
this ordering requirement or auto-create OpenBao policies and auth mounts.
Initialization, unsealing and backend policy configuration remain documented
bootstrap operations, with credentials outside Git.

Existing secret-store has prune:false. Consequently the old, redundant custom
binding may remain in an already-running cluster after reconciliation. New
clusters do not need it. Verify that the official chart-owned binding grants
the expected server account TokenReview rights before removing an existing
custom binding. The refactor does not delete live RBAC or recovery material.

## What remains cluster-specific

The scan retained API addresses/ports, node names and device selections,
Ceph topology, replica counts, reduced lab storage/resources/retention, workload
scheduling, and metrics-server's explicitly documented lab-only kubelet TLS
exception. These would be incorrect defaults for other environments.

The cluster still owns which components are selected, Git sourceRef settings,
Flux dependsOn and health checks, storage readiness, and its chosen pruning
policy. Flux Kustomization timeouts are separate from HelmRelease operation
timeouts and were not removed. Cilium's bootstrap dependency adjustment remains
local. The minimal lab still needs a source because it has no shared foundation.

Existing namespace identities and owners were preserved. The old full-platform
composition includes Namespace/demo in both foundation and the standalone demo
component; this duplicate declaration remains unchanged rather than risking
namespace deletion during a pruning/ownership transition. New compositions
should choose a single intended namespace owner. Selecting the shared namespace
bundle creates namespaces only; it does not enable every infrastructure tool.

## Verification

- The standard validator passed **103 Kustomize builds**, the existing 37
  selected Flux child definitions and all 25 selected HelmRelease health gates.
- Captured before/after builds of all selected full-platform paths, keyed by
  API/kind/namespace/name. Compared them after normalizing Flux defaults:
  absent suspend equals false, and an omitted Helm timeout equals 5m.
- Before: 143 unique selected object identities. After: 142. The only removed
  identity is the redundant custom openbao-token-review binding. No new selected
  identities were introduced by moving definitions to reusable components.
- All other normalized resources match, except the OpenBao values ConfigMap's
  explicit authDelegator:true, which equals the pinned chart's previous default.
- Rendered the pinned official OpenBao chart with final values and asserted
  its binding grants exactly system:auth-delegator to secrets/openbao. The chart
  emits its existing coalescing warnings for the structured HA configuration;
  those values were not changed by this refactor and this check targets RBAC.
- Independently built the previous and current minimal iximiuz-labs Cilium
  overlay; its effective resources match after normalizing the same defaults.
- Built the reusable store alone and confirmed it contains a ServiceAccount and
  SecretStore, with no verification ExternalSecret included implicitly.
- Dependency graph and health gates are unchanged. Gateway CRD definitions,
  namespace objects, smoke-test resources, PostgreSQL's selected TLS references,
  resource sizing, storage classes and backend connection settings are preserved.
- Whitespace checks passed. See the [sanitized comparison evidence](evidence/template-reuse-2026-11-01.json).

No new end-to-end live deployment claim is made: the checks establish effective
manifest equivalence and chart-provided RBAC, not a new backend bootstrap run.
