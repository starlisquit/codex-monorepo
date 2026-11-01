# Cilium deployment modes and cluster values

Select this directory for the shared Cilium HelmRelease and mandatory defaults.
The release also references optional ConfigMap `kube-system/cilium-cluster-values`
with key `values.yaml`. A consuming cluster can generate that ConfigMap directly;
no patch to `valuesFrom` is needed. Shared values merge first, cluster values
second; inline HelmRelease values, if added, retain Flux's highest precedence.

The ConfigMap must retain its stable name and the label
`reconcile.fluxcd.io/watch: Enabled`. See the actual iximiuz cluster wrappers for
complete configMapGenerator examples. Only absence of the optional ConfigMap is
ignored: missing keys, invalid YAML and other read errors still fail.

Default mode retains the Helm dependency on monitoring CRDs. For native CNI
bootstrap, select the [bootstrap component](opt-in/bootstrap/README.md)
in the cluster wrapper's `components` list. This is an opt-in mode selection,
not a boolean in Cilium's Helm values. The caller must retain appropriate
Flux readiness gates or disable unavailable chart integrations.

## Hubble central PKI

Hubble certificate automation uses `method: certmanager` with explicit
`ClusterIssuer/platform-workload-ca` and rotating leaf keys. It covers the node
server and Relay client, plus Relay/UI/metrics serving certificates whenever
those chart features are enabled. Kubernetes/bootstrap CA ownership is unchanged.
Provision cert-manager, the issuer and public trust before the final Cilium
release. The networking seed keeps Hubble and its certificate automation disabled
until those prerequisites exist. Restart agents/operator or use the chart's
rollout settings when changing startup configuration; existing deployments also
need a deliberate CA trust handover.

[Focused runtime verification](../../../docs/findings/central-pki-network-2026-11-01.md)
proved TLS/mTLS, 3/3 Relay peers, real flow RPCs and leaf hot renewal without Pod
restarts. The test additionally enabled Relay serving TLS/mTLS; that listener
remains an explicit cluster choice. No unsafe TLS-verification bypass was used.
