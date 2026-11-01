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
bootstrap, select the [bootstrap component](../../../components/cilium-bootstrap/README.md)
in the cluster wrapper's `components` list. This is an opt-in mode selection,
not a boolean in Cilium's Helm values. The caller must retain appropriate
Flux readiness gates or disable unavailable chart integrations.
