# Flux and Helm findings

## Standalone Flux UI still needs APIs

The standalone web server (`web.serverOnly: true`) initially crashed with:
`failed to determine if *v1.FluxInstance is namespaced`.
`installCRDs: true` is now set. No FluxInstance is created and no lifecycle
controller is enabled; Flux manages its own installation from committed manifests.
API definitions and an active lifecycle controller are different things.

## Namespace defaults are real dependencies

Trust-manager tried to create a Role in a nonexistent `cert-manager` namespace.
The shared values now set `app.trust.namespace: certificates`, matching this
repository, and its HelmRelease depends on cert-manager. A downstream cluster
that changes namespace layout must change both references.

## Render with the runtime's Helm generation

The demo rendered successfully with local Helm 3 but failed under the live Helm
4 renderer: `index of untyped nil` in the Collector's deprecated-component-name
rewrite helper. `config.service.pipelines.profiles: null` remained visible to
that helper. Rendering success under a different major version was insufficient.

The pinned demo now uses an explicit Collector `alternateConfig` with only
metrics, logs, and traces pipelines. It preserves the intended scrapers,
processors, health check and native-agent exporters without relying on null
merging. When upgrading the chart, compare its defaults with this explicit
configuration; new upstream defaults are not adopted automatically. End-to-end
SDK ingestion remained unverified at the time this record was written.

## Reconciliation and interruption

A source revision change can temporarily make downstream dependencies not Ready.
Reconcile foundations first and follow the readiness graph. A long-running
health check may still be evaluating an earlier source revision; annotating the
object does not necessarily interrupt that in-flight attempt. Read its
conditions, observed generation, and revision before diagnosing a new failure.

An API interruption left Helm in `pending-install`. After recovery the Helm
controller reported its unlock action and completed an upgrade. Inspect Flux
conditions before reaching for manual Helm operations. Do not delete Helm
release Secrets as a generic repair: they contain release state and credentials.

Kustomize patches are now stored as readable YAML blocks. Cluster-specific
replica, sizing, and placement choices remain in cluster overlays. Shared
HelmReleases remain suspended until selected by an overlay.

The documentation/template update rendered trust-manager, Rook operator, the
Ceph CSI driver chart, and the demo under both the local Helm 3 renderer and
Helm 4.0.0. The Collector renders exactly three non-null pipelines in both.
This checks both major-version paths, not every version of the embedded Helm
library, and does not replace runtime export verification.
