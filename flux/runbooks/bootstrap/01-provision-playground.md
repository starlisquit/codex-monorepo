# 1. Provision and prepare the playground

Prerequisites: an authenticated iximiuz Labs account with a sufficient resource
budget, `labctl` on your workstation, Git, kubectl, Helm, Flux CLI, and access to
this repository. The kubeadm base provides kubectl and Helm on `dev-machine`.
The committed controllers are Flux 2.10.0 and Cilium is pinned to 1.20.4.
Install the matching Flux CLI on the amd64 `dev-machine` if it is missing:

```sh
flux_download_dir=$(mktemp -d)
curl -fsSL https://github.com/fluxcd/flux2/releases/download/v2.10.0/flux_2.10.0_linux_amd64.tar.gz -o "$flux_download_dir/flux_2.10.0_linux_amd64.tar.gz"
curl -fsSL https://github.com/fluxcd/flux2/releases/download/v2.10.0/flux_2.10.0_checksums.txt -o "$flux_download_dir/checksums.txt"
(cd "$flux_download_dir" && sha256sum --ignore-missing -c checksums.txt)
mkdir -p "$HOME/.local/bin"
tar -xzf "$flux_download_dir/flux_2.10.0_linux_amd64.tar.gz" -C "$HOME/.local/bin" flux
export PATH="$HOME/.local/bin:$PATH"
flux version --client
rm -r "$flux_download_dir"
```

Use the correct release asset for another operating system or architecture.

## Provision

The saved private playground definition already contains the next-run sizing:

```sh
labctl playground start codex-platform-243e14fd --open
```

For an independently owned definition, copy and rename the complete manifest:

```sh
git clone https://github.com/starlisquit/codex-monorepo.git
cd codex-monorepo
cp flux/runbooks/bootstrap/iximiuz-playground.yaml /tmp/my-codex-platform.yaml
yq -i '.name = "my-codex-platform"' /tmp/my-codex-platform.yaml
labctl playground create my-codex-platform --base k8s-omni -f /tmp/my-codex-platform.yaml
# Use the full name printed by create, including its generated suffix:
labctl playground start FULL_NAME_FROM_CREATE --open
```

The full name above is an explicit user-supplied placeholder. The file includes
all inherited kubeadm initialization tasks; overriding the task map with just one
changed task failed because its dependencies were absent. Its kubeadm command
uses `--skip-phases=addon/kube-proxy`. There is no preinstalled CNI.

## Check effective resources and raw disks

Open `dev-machine`; wait for kubeadm initialization and worker joins:

```sh
kubectl get nodes -o wide
kubectl get nodes -o custom-columns=NAME:.metadata.name,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory
```

NotReady is expected before Cilium. On **each** of `cplane-01`, `node-01`, and
`node-02`, run as root:

```sh
free -m
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS
command -v lvm
modprobe rbd
```

Expected: `/dev/vda` is the mounted 20 GiB system disk and `/dev/vdb` is a raw,
unmounted 25 GiB disk with no filesystem. Stop if that does not match: Rook will
consume `vdb`. Do not wipe or repurpose a mounted or previously used disk.

The new manifest prepares LVM/RBD automatically. For an older definition that
lacks those tasks, run on every node:

```sh
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y lvm2
modprobe rbd
```

Verify the direct API address is `172.16.0.2:6443`. The overlay hard-codes that
address and the node names. For a different network, update
`clusters/iximiuz-platform/cilium/values.yaml`, the Ceph node selection, demo
worker affinity, and relevant runbook commands before bootstrap.

The control plane requests 4 vCPUs/6 GiB; workers 2 vCPUs/4608 MiB; dev machine
1 vCPU/1 GiB. These defaults affect **future** VMs. The currently running play
still has its original equal-size Kubernetes nodes. See
[sizing findings](../../docs/architecture/playground-sizing.md) for resource caps
and the unresolved API slowness.
