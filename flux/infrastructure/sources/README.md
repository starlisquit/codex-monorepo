# Individually selectable Flux sources

Each subdirectory is an independently buildable HelmRepository or OCIRepository
base named after the source's metadata.name. Select only sources used by the
chosen templates. For example `infrastructure/sources/litellm` creates only the
LiteLLM OCI source, and `infrastructure/sources/cilium` creates only Cilium's
Helm repository. Sources retain their original names, versions, URLs and
flux-system namespace.

The root Kustomization is an optional all-sources convenience bundle, not a
prerequisite. Each run foundation selects only the sources it needs. When several releases share a
source, select it once under their common foundation rather than duplicating
its identity in multiple consumers.

Templates keep their native HelmRelease sourceRef/chartRef. Installing or
creating a namespace does not create a Flux source. Include the matching source
base in the deployment wrapper or an earlier foundation.
