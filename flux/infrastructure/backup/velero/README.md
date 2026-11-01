# Velero

Select [this namespace base](../../namespaces/velero/kustomization.yaml) in foundation
or the deployment wrapper before this template. No all-namespaces bundle is
required; this directory does not create its own namespace.

Pinned official Helm chart **12.2.2**, Velero **1.18.2**, from
<https://vmware-tanzu.github.io/helm-charts/>. The chart archive was checked against
its published index SHA-256 and rendered with Helm 4. Base and S3 example renders
were validated locally; there is no running playground or tested backup/restore.

The shared HelmRelease reconciles when included. The full-platform overlay selects
Velero normally, without a suspension gate. It waits for foundation, monitoring
CRDs and Cilium. Metrics use a ServiceMonitor for the VictoriaMetrics stack.

## Default state is not data protection

The base creates a server deployment and CRDs, but no BackupStorageLocation,
VolumeSnapshotLocation, node-agent DaemonSet, backup or schedule. It does not
create credentials. **Configure the backend to enable usable backups**; a deployment
without a valid storage location cannot protect your cluster.

Flux Helm CRD CreateReplace handles chart CRDs; the chart's separate CRD-upgrade
Job is disabled to avoid duplicate owners/jobs. Destructive CRD cleanup is disabled.
The parent uses prune=false as an extra retention boundary, not a backup policy.
Review CRD, namespace and object-store retention before uninstalling.

Velero requests 100m CPU/256 MiB RAM with a 512 MiB memory limit and worker affinity.
These are initial lab settings; backup workloads and data movement need separate
capacity planning. Default chart RBAC grants broad cluster-administrator rights
for discovery and restore. Restrict access to its namespace/service account and
review the render before production use.

## Configure S3-compatible object storage

`opt-in/s3/values.example.yaml` is **excluded** from Kustomize. Copy it to a cluster-owned
values file, replace bucket/region/HTTPS endpoint, and provision an existing Secret
`velero-cloud-credentials` in namespace `velero`, with the credential file under
key `cloud`. Do not put access keys in Git. Prefer provider workload identity when
available; adapt `credentials.useSecret` accordingly.

The example pins AWS plugin **v1.14.4**, whose documented compatibility family is
Velero 1.18.x. It only configures object storage, not AWS EBS snapshots. The plugin
also supports compatible S3 services, subject to provider-specific configuration.
For Ceph RGW, review the plugin's documented checksum settings and validate actual
uploads/downloads; the current Rook deployment does not provision RGW.

Use an existing off-cluster bucket to survive destroying this playground. An
in-cluster MinIO/RGW bucket in the same failure domain does not accomplish that.
Use least-privilege bucket credentials, storage-side encryption and deliberate
retention. Metadata backups can contain Kubernetes Secrets; protect them as such.

For a privately signed object-store endpoint, configure the BSL's `caCertRef` to a
Secret containing **public CA certificates only** in `velero`. The shared
trust-manager ConfigMap is not automatically trusted by the provider plugin.
Keep HTTPS verification enabled; do not copy the CA signing key into Velero or
set insecureSkipTLSVerify just to clear a validation error.

Follow the [enablement and restore-test runbook](../../../runbooks/operations/velero.md).

## Ceph/PVC data is a separate decision

A Kubernetes object backup alone does not copy PVC contents. The supplied example
Backup explicitly disables volume snapshots and file-system backups. To protect
PVC data, configure and test one of:

- CSI snapshots with a functioning snapshot controller, matching VolumeSnapshotClass,
  RBD CSI support, and appropriate deletion/retention policies. Same-Ceph snapshots
  remain dependent on that Ceph cluster; snapshots alone are not off-cluster copies.
- Velero node-agent/file-system backup or CSI snapshot data movement to off-cluster
  object storage, with the required privileged mounts, resources and credentials.

The templates do not enable either. Do not assume existing Ceph CSI drivers imply
snapshot-controller installation or a tested recovery path. PostgreSQL consistency
and OpenBao Raft recovery also need application-aware backup procedures. No
claim of recoverable database, secrets-engine or PVC data is made here.

References: [Velero documentation](https://velero.io/docs/v1.18/),
[AWS plugin compatibility](https://github.com/vmware-tanzu/velero-plugin-for-aws#compatibility),
[Helm chart](https://github.com/vmware-tanzu/helm-charts/tree/main/charts/velero).
