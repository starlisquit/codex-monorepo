# Native template overrides and Cilium bootstrap — 2026-11-01

> Layout and namespace ownership were subsequently consolidated; see
> [the layout refactor](template-layout-2026-11-01.md). Historical validation results below remain unchanged.

The repeated valuesFrom append patch is replaced by native Flux support across
all 31 HelmRelease templates. Cilium dependency removal is replaced by an
explicit opt-in Kustomize Component. No extra templating engine, custom CRD
fields or fake Helm-value boolean is introduced.

## Native optional cluster values

Each HelmRelease references its existing mandatory defaults ConfigMap first,
then `<HelmRelease.metadata.name>-cluster-values` with `optional: true` and key
`values.yaml`. References resolve in the release's own namespace. A cluster can
create that ConfigMap directly with a stable configMapGenerator name and the
`reconcile.fluxcd.io/watch: Enabled` label. It need not patch the release's
valuesFrom list or generate an empty placeholder ConfigMap.

Merge precedence is shared values, then cluster values, then inline spec.values.
The optional flag ignores an absent ConfigMap. It does not ignore a missing
values key, malformed values or transient API errors. Removing a cluster-values
ConfigMap drops that override layer, so installations that require its settings
must ensure it is provisioned by their deployment configuration.

Existing Cilium (both labs), Ceph, NATS, observability, OpenBao and Valkey cluster
wrappers now only generate their actual values; their append patches are gone.
The existing names, namespaces, contents and watch labels are retained. The
Velero operations runbook now uses the same native mechanism rather than
instructing users to construct another HelmRelease patch.

## Cilium dependency mode

The shared Cilium release retains its normal monitoring-CRD dependency. Select
`flux/infrastructure/networking/cilium/opt-in/bootstrap` in the consumer's components list to remove
that dependency list. The component targets Cilium only; other releases retain
their dependency guards. Both existing iximiuz Cilium wrappers now select it,
preserving their prior bootstrap behavior without copying a JSON patch.

The full-platform cluster retains its outer Flux readiness gates. The minimal
lab retains values disabling monitoring/Gateway integrations whose prerequisites
are absent. The component itself does not disable those integrations or make
runtime prerequisites disappear. Omit it for normal dependency behavior.

A boolean such as `dependsOn.enabled` in a chart values file cannot implement
this feature: Helm values configure the chart, while the containing HelmRelease
is reconciled by Flux. Kustomize Components provide a native inclusion switch;
Kustomize does not evaluate arbitrary boolean conditionals in static YAML.

See the [component documentation](../../infrastructure/networking/cilium/opt-in/bootstrap/README.md)
and [Cilium template documentation](../../infrastructure/networking/cilium/README.md).

## Verification

- All 103 Kustomize builds passed, including shared Cilium in default mode and
  both cluster consumers using the component. Components are composed into
  those consumers rather than built as standalone Kustomizations.
- The 37 selected Flux child definitions / 25 selected HelmReleases still pass
  dependency and health-check coverage validation.
- Checked all 31 references: existing shared ConfigMap mandatory, optional
  cluster ConfigMap last, exact namespace/name contract, native boolean true.
- Inspected the vendored HelmRelease v2 CRD schema: optional is supported and
  explicitly only ignores missing referenced resources, not key/path/transient
  errors. No invented mode field is emitted into HelmRelease resources.
- Default Cilium retains its monitoring dependency. Both opt-in builds omit it,
  while retaining their cluster values ConfigMaps and both value layers.
- Compared before/after selected manifests by object identity. All 142 selected
  identities are preserved. Resolving optional ConfigMap references against the
  built manifests preserves every selected resource's effective configuration.
  Present override references differ only in becoming optional; absent optional
  references add no active value layer.
- Independently compared the minimal iximiuz-labs Cilium overlay against its
  previous committed version; effective values and dependencies are unchanged.
- Whitespace checks passed. [Sanitized evidence](evidence/native-template-options-2026-11-01.json)
  records these results.

This is configuration rendering/schema verification, not a new live Flux
controller run. No playground was created. Chart versions, chart values,
credentials, runtime sizing and existing readiness orchestration were unchanged.
