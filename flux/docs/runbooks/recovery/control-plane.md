# Control-plane/API incident handling

The current API slowness diagnosis was explicitly paused by the user. This
runbook records the safe starting checks and the earlier recovery boundaries;
it does not claim that increasing a resource request fixed the running play.

## Bound the diagnosis

From `dev-machine`:

```sh
kubectl --request-timeout=5s get --raw /readyz
kubectl --request-timeout=5s get nodes
```

On `cplane-01` as root, independently of Kubernetes API availability:

```sh
free -m
uptime
df -h /
ps -eo pid,comm,pcpu,rss --sort=-rss | head -15
journalctl -u kubelet -n 80 --no-pager
crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps -a --name etcd
crictl --runtime-endpoint unix:///run/containerd/containerd.sock ps -a --name kube-apiserver
ss -ltnp | grep -E '2379|2380|2381|6443'
```

These show resource pressure and the state of existing processes. Do not dump
credential files, kubeconfigs, or arbitrary Secret contents into shared logs.
If the guest command channel times out but the VM is reachable, an independent
worker's SSH path may still work; this was observed, not a universal platform
availability guarantee.

## Static-pod changes

Do not edit etcd's listener as an incidental monitoring tweak. An earlier edit
interrupted the API and required recovery. Before any planned static-pod change,
retain the original manifest **outside** `/etc/kubernetes/manifests`, confirm data
backup/recovery, and change one component at a time. Backup files inside the
watched directory can themselves be interpreted as manifests.

For the specific reverted metrics edit, the saved original manifest is at
`/root/manifests-before-metrics/etcd.yaml` on the recorded control-plane VM. If
that same edit is still present and that backup is verified, restoring it is:

```sh
cp -a /root/manifests-before-metrics/etcd.yaml /etc/kubernetes/manifests/etcd.yaml
```

Do not use this path on a different play without establishing where its backup
came from. Do not delete `/var/lib/etcd`, regenerate the cluster, run kubeadm reset,
or use a new empty etcd data directory to clear a timeout.

The historical incident also used a temporary etcd process against the existing
data while bringing the original static Pod back. That was incident-specific,
not a tested general recovery recipe. Never run concurrent etcd processes against
the same data directory; confirm ownership and stop any temporary process before
returning to normal management. Use an appropriate etcd recovery procedure if
data corruption or quorum loss is actually established.

## Post-recovery checks

After the API is reachable:

```sh
kubectl --request-timeout=10s get --raw /readyz
kubectl get nodes
kubectl -n kube-system get pods -o wide
flux check
flux get all -A
kubectl get pvc -A
kubectl -n rook-ceph exec deploy/rook-ceph-tools -- ceph status
```

During the recorded recovery, restarting the control-plane Cilium agent resolved
stale Service reachability after kubelet/API restarts. That is an observation,
not a reason to restart the whole CNI for every timeout. Inspect `cilium-dbg status`,
Service backends, endpoints, and the affected node before an intervention.

Future playgrounds use the [larger control-plane allocation](../../architecture/playground-sizing.md).
Changing a saved playground definition does not hot-resize existing VMs.
