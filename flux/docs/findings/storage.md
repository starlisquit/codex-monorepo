# Storage findings

## Explicit disks, not the system disk

The original nodes exposed only a mounted 30 GiB `/dev/vda`. Ceph had no eligible
raw devices. The full play adds a raw 25 GiB `/dev/vdb` to each Kubernetes node.
Rook selects only those three named devices with `useAllNodes: false` and
`useAllDevices: false`. Never turn on blanket device selection to work around a
missing disk. Ceph consumes and changes the selected raw devices.

Install `lvm2` and load the `rbd` module on all storage/client nodes before rollout.
The future-playground manifest includes these preparation tasks. Device names
follow drive order in the iximiuz manifest; verify them after every recreation.

## Rook and CSI are distinct layers

For the pinned Rook 1.21.1 chart, deploying the operator also deployed
`ceph-csi-controller-manager` and its API CRDs, but **no CSI drivers** were created.
Connection/Profile resources alone did not produce a Kubernetes CSIDriver.
PVCs remained Pending until the separate `ceph-csi-drivers` 1.1.0 chart installed
a Driver CR named `rook-ceph.rbd.csi.ceph.com`.

The Rook-compatible driver values must point to
`rook-csi-operator-image-set-configmap` and use the `rook-ceph` provisioner prefix.
Shared defaults now permit RBD and CephFS with two controller replicas; the lab
explicitly enables only RBD and uses one controller replica. The
`csi.createCsiOperatorResources` setting manages the associated connection/profile
resources; it does not replace installation of the driver chart.

References: [Rook driver chart instructions](https://github.com/rook/rook/blob/v1.21.1/Documentation/Helm-Charts/csi-drivers-chart.md),
[recommended values](https://github.com/rook/rook/blob/v1.21.1/deploy/charts/ceph-csi-drivers/values.yaml).

## Readiness and capacity

Three 25 GiB OSDs provide 75 GiB raw capacity and approximately 25 GiB before
overhead with a size-three replicated pool. The lab retains replication across
three hosts, omits CephFS/RGW workloads, and reduces application PVC sizes.
Thin provisioning does not make data capacity unlimited; watch actual pool usage.

A HelmRelease can become Ready while the CephCluster is still forming quorum.
The explicit cluster/pool gates and persistent-volume Job catch this distinction.
The Job passed after dynamic provisioning, attach, mount, write, sync, and read.
Its success is a historical smoke test, not a continuous storage monitor; delete
only that completed Job to rerun it through Flux, retaining its test PVC.

Ceph 20.2.4 reported insecure-key compatibility warnings with the chart's AES CSI
key configuration on kernel 6.1. Rook's values explicitly require AES before
kernel 7.0. We did not suppress the warning or prove that every warning is safe.
The lab gate accepts HEALTH_WARN and rejects HEALTH_ERR; inspect health detail.

Pruning is disabled for data-bearing infrastructure. PVC reclaim policies and
explicit deletion still matter. A play snapshot is not an independent backup.
