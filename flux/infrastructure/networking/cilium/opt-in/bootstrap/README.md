# Cilium bootstrap component

Opt-in Kustomize Component that removes only Cilium's HelmRelease `dependsOn`
list. Without this component, the shared template still waits for
`observability/prometheus-operator-crds`.

Select it in the consuming cluster wrapper:

```yaml
resources:
- ../../../infrastructure/networking/cilium
components:
- ../../../infrastructure/networking/cilium/opt-in/bootstrap
```

This replaces a repeated JSON patch with an explicit mode selection. Components
are applied by a consuming Kustomization, rather than built as standalone
Kustomizations. Both iximiuz wrappers exercise this component in validation.

Only use this mode when the cluster's Flux dependency/health gates already
supply the prerequisites, or a minimal bootstrap disables features requiring
those prerequisites. It does not disable ServiceMonitors, Gateway API or TLS
features by itself. The full-platform wrapper keeps its existing Flux gates;
the minimal lab disables unavailable integrations in its cluster values.

There is no HelmRelease `dependsOn.enabled` or Kustomize boolean expression.
Adding a similarly named Helm value cannot change the surrounding HelmRelease.
Normal dependency behavior is restored by omitting this component; it does not
relax dependency checks for any other release.
