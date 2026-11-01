# iximiuz Labs cluster

Three kubeadm nodes with containerd, initially provisioned without a CNI using the
private `codex-flux-no-cni-27075bc5` playground. Cilium 1.20.4 is installed with Helm
to establish networking before Flux starts, then reconciled by Flux under the
same Helm release name and namespace.

Flux 2.10.0 reads the public repository over HTTPS without credentials, tracking
`main` at `flux/clusters/iximiuz-labs`. Its controllers manage their own manifests.
Other infrastructure templates are not enabled by this cluster.

The Cilium overlay sets the direct API endpoint to `172.16.0.2:6443`, Kubernetes
IPAM, and one operator replica. Gateway API and ServiceMonitors are disabled until
their CRDs are installed. Hubble, Envoy, and kube-proxy replacement are enabled.
Cilium reconciliation uses `prune: false` to protect networking from accidental
Git removal. The playground-provided kube-proxy DaemonSet and ConfigMap have been
removed. Cilium handles ClusterIP and NodePort routing on all three nodes.
The kube-proxy built-in `--cleanup` was run on each node; kubelet-owned firewall
and canary chains remain intact.

## Access

Open the play and use the `dev-machine` terminal. The `laborant` user already has
kubectl, Helm, Flux, and kubeconfig configured. Do not commit kubeconfigs or tokens.

## Recreate the bootstrap

After provisioning the same network and installing Cilium using the merged base
values and cluster overrides, remove the playground-provided kube-proxy:

```sh
kubectl -n kube-system delete daemonset kube-proxy
kubectl -n kube-system delete configmap kube-proxy
```

Run the matching kube-proxy image with `--cleanup` in a privileged, host-network
container on each node to remove stale Service rules before checking connectivity.
For a fresh kubeadm installation under your control, use
`kubeadm init --skip-phases=addon/kube-proxy` instead. The upstream playground
initialization still installs kube-proxy, so repeat the migration for a new play.

Then install Flux:

```sh
git clone https://github.com/starlisquit/codex-monorepo.git
cd codex-monorepo
kubectl apply --server-side -f flux/clusters/iximiuz-labs/flux-system/gotk-components.yaml
kubectl apply -f flux/clusters/iximiuz-labs/flux-system/gotk-sync.yaml
flux get all -A
```

This playground is temporary lab infrastructure. Check its current lifetime in
iximiuz Labs and stop it when finished. Recreating a play requires bootstrapping
again; Git contains the desired cluster configuration.
