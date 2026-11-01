# 2. Install Cilium and bootstrap Flux

Use `dev-machine` with its existing kubeconfig. Clone the repository there if
needed and enter its root. Make sure the desired manifests are already on the
branch Flux will fetch; applying unpushed local files cannot make them Git-managed.

## Fresh cluster without kube-proxy

```sh
git clone https://github.com/starlisquit/codex-monorepo.git
cd codex-monorepo
kubectl config current-context
kubectl -n kube-system get daemonset kube-proxy --ignore-not-found
flux/runbooks/scripts/bootstrap-cilium.sh flux/clusters/iximiuz-platform 172.16.0.2 6443
```

The kube-proxy query should return no resource. The helper installs Helm release
`cilium` in `kube-system`, merges shared values and cluster overrides, then disables
Gateway API and ServiceMonitor creation for the initial seed. Those CRDs do not
exist yet. Hubble and its central CA bundle are also deferred until Flux installs
cert-manager and the platform PKI. It retains the direct API endpoint,
kube-proxy replacement, and WireGuard encryption.

Verify replacement on each agent:

```sh
for pod in $(kubectl -n kube-system get pods -l k8s-app=cilium -o name); do
  echo "$pod"
  kubectl -n kube-system exec "$pod" -- cilium-dbg status --verbose
done
```

Expect replacement True, ready agents, and Service support enabled.

## Existing kube-proxy cluster

The seed helper intentionally stops if kube-proxy exists. First inspect Cilium
and plan the transition using the [migration record](../../docs/findings/kube-proxy-migration.md).
Do not delete kube-proxy before replacement is configured on all nodes. Once it
is confirmed, back up and remove the old resources from `dev-machine`:

```sh
mkdir -p /home/laborant/cluster-backups
kubectl -n kube-system get ds kube-proxy -o yaml > /home/laborant/cluster-backups/kube-proxy-daemonset.yaml
kubectl -n kube-system get cm kube-proxy -o yaml > /home/laborant/cluster-backups/kube-proxy-configmap.yaml
kubectl -n kube-system delete daemonset kube-proxy
kubectl -n kube-system delete configmap kube-proxy
kubectl -n kube-system wait --for=delete pod -l k8s-app=kube-proxy --timeout=1m
```

As root on every node, run the matching cached kube-proxy image's cleanup. The
version below is the one used in the recorded migration; substitute the version
from your saved DaemonSet if different:

```sh
ctr -n k8s.io run --rm --privileged --net-host \
  registry.k8s.io/kube-proxy:v1.37.2 kube-proxy-cleanup \
  /usr/local/bin/kube-proxy --cleanup
```

Do not flush all iptables tables. Kubelet firewall/canary chains are expected to
remain. Verify DNS, ClusterIP, and NodePort traffic after cleanup.

## Bootstrap Flux

```sh
flux version --client
flux/runbooks/scripts/bootstrap-flux.sh flux/clusters/iximiuz-platform
flux get sources git -A
flux get kustomizations -A
```

The GitRepository is public HTTPS, branch `main`, with no credential Secret.
For a private repository, configure an appropriate read credential and source
Secret reference outside Git. Update `gotk-sync.yaml` for another repository or
path before applying it.

Flux installs monitoring and Gateway API CRDs, then takes over the existing
Cilium Helm release with its full settings. The standalone UI does not manage
Flux's lifecycle. Continue with [storage gates](03-platform-and-storage.md).
