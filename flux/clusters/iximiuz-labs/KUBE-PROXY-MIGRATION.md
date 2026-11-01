# Cilium kube-proxy replacement

## Outcome

On 2026-11-01, the iximiuz Labs cluster was migrated to Cilium-only Service
routing. The kube-proxy DaemonSet, its three Pods, and its ConfigMap were removed.
The matching kube-proxy binary's built-in cleanup removed its old routing rules
on all three nodes. Cilium and Flux remained healthy after the migration.

The cluster was initially provisioned without a CNI using the private
`codex-flux-no-cni-27075bc5` playground. The kubeadm playground still installed
kube-proxy. Cilium was installed with Helm to establish Pod networking, then Flux
took over the same `kube-system/cilium` release and successfully reconciled Helm
revision 2. Enabling Cilium's replacement does not remove an existing kube-proxy
DaemonSet automatically.

## Configuration and ownership

| Setting | Value |
| --- | --- |
| Kubernetes nodes | `cplane-01`, `node-01`, `node-02` |
| Node addresses | `172.16.0.2`, `172.16.0.3`, `172.16.0.4` |
| Container runtime | containerd |
| Cilium chart and application | `1.20.4` |
| Flux | `2.10.0` |
| kube-proxy image used for cleanup | `registry.k8s.io/kube-proxy:v1.37.2` |
| `kubeProxyReplacement` | `true` |
| Direct API endpoint | `172.16.0.2:6443` |
| IPAM | `kubernetes` |
| Git branch | `main` |
| Flux cluster path | `flux/clusters/iximiuz-labs` |

The shared [Cilium values](../../infrastructure/networking/cilium/values.yaml)
enable replacement. The [cluster overlay](cilium/kustomization.yaml) enables the
HelmRelease and loads [cluster values](cilium/values.yaml) after the shared values.
The direct API endpoint lets Cilium reach Kubernetes without Service routing.

Flux's `flux-system` Kustomization creates the `cilium` Kustomization, which
reconciles the HelmRepository, values ConfigMaps, and HelmRelease. The Helm
controller manages Cilium upgrades. Cilium reconciliation has `prune: false` to
protect networking from accidental Git removal. Kube-proxy removal was an
administrative migration, not a resource deletion enforced continuously by Flux.

## Procedure used

Run Kubernetes commands from the playground's `dev-machine` as `laborant`.
Before removal, verify replacement on every Cilium agent:

```sh
for pod in $(kubectl -n kube-system get pods -l k8s-app=cilium -o name); do
  echo "$pod"
  kubectl -n kube-system exec "$pod" -- cilium-dbg status --verbose
done
```

All three agents reported `KubeProxyReplacement: True`, full socket load balancing,
and ClusterIP, NodePort, and HostPort enabled, with zero degraded modules.

Back up the existing resources outside Git, then remove kube-proxy:

```sh
mkdir -p /home/laborant/cluster-backups
kubectl -n kube-system get ds kube-proxy -o yaml \
  > /home/laborant/cluster-backups/kube-proxy-daemonset.yaml
kubectl -n kube-system get cm kube-proxy -o yaml \
  > /home/laborant/cluster-backups/kube-proxy-configmap.yaml
kubectl -n kube-system delete daemonset kube-proxy
kubectl -n kube-system delete configmap kube-proxy
kubectl -n kube-system wait --for=delete pod -l k8s-app=kube-proxy --timeout=20s
```

Run the following as root on **each** of `cplane-01`, `node-01`, and `node-02`.
The image below matched the removed DaemonSet and was already cached. For another
cluster, use its actual kube-proxy version.

```sh
ctr -n k8s.io run --rm --privileged --net-host \
  registry.k8s.io/kube-proxy:v1.37.2 kube-proxy-cleanup \
  /usr/local/bin/kube-proxy --cleanup
```

This uses kube-proxy's own cleanup instead of flushing host firewall tables.
Inspection afterward found no old Service chains on the inspected control-plane
node. Kubelet-owned `KUBE-FIREWALL`, canary, and hint chains remained; their names
alone do not indicate that kube-proxy is still running.

## Validation performed

A temporary nginx Pod was pinned to `node-01` and exposed through a NodePort
Service. A BusyBox test Pod was pinned to each of the three nodes. Every test Pod
successfully:

- Resolved `kubernetes.default.svc.cluster.local` through cluster DNS.
- Resolved `github.com` through cluster DNS.
- Reached nginx through its Service DNS name and ClusterIP.
- Reached nginx through the NodePort on all three node addresses.

All three test Pods completed with `PASS`. This includes cross-node Service
traffic from the control plane and `node-02` to the backend on `node-01`.
The temporary `network-verification` namespace and its resources were then deleted.
These checks cover the exercised DNS, ClusterIP, and NodePort paths; they are not
a full Cilium connectivity conformance suite.

The final status checks were:

```sh
kubectl get nodes
kubectl -n kube-system get daemonset,pods -l k8s-app=kube-proxy
flux get all -A
```

All three nodes were Ready. No kube-proxy DaemonSet or Pods remained. The Git
source, Cilium Helm source/chart/release, and both Flux Kustomizations were Ready.

## Recovery and recreation

The original DaemonSet and ConfigMap backups remain on `dev-machine` under
`/home/laborant/cluster-backups`. If recovery requires reinstating the prior
kube-proxy deployment, restore the ConfigMap and then the DaemonSet:

```sh
kubectl apply -f /home/laborant/cluster-backups/kube-proxy-configmap.yaml
kubectl apply -f /home/laborant/cluster-backups/kube-proxy-daemonset.yaml
kubectl -n kube-system rollout status daemonset/kube-proxy --timeout=60s
```

This restores the original coexistence configuration; it does not turn off
Cilium's replacement. Any change to Cilium's desired values must also be made in
Git so Flux does not overwrite it. Recheck DNS and Service traffic after recovery.
The restoration procedure was documented but was not exercised during this
successful migration.

The upstream playground initialization still installs kube-proxy. Repeat the
migration after creating a new play. For a fresh kubeadm installation you control,
skip the addon at initialization instead:

```sh
kubeadm init --skip-phases=addon/kube-proxy # plus the cluster's other init options
```

See the [cluster README](README.md) for the Flux bootstrap sequence.
