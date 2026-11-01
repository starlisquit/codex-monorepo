# Configure and verify Velero

Prerequisites: a stable cluster, monitoring CRDs, an existing external backup
bucket, narrowly scoped access to it, and a compatible Velero CLI. Read the
[component limits](../../infrastructure/backup/velero/README.md). The last
playground is destroyed; this is an unexercised procedure, not a recovery result.

## Prepare storage and credentials

From the repo root, after reviewing and filling in the excluded example:

```sh
cp flux/infrastructure/backup/velero/values-s3.example.yaml \
  flux/clusters/iximiuz-platform/velero/values.yaml
```

Edit that file to use your real bucket, region and HTTPS endpoint before deploying.
Create the namespace and provision the credential through your approved secret
workflow. For a preexisting local credential file, outside the repository:

```sh
kubectl apply -f flux/infrastructure/backup/velero/namespace.yaml
kubectl -n velero create secret generic velero-cloud-credentials \
  --from-file=cloud=/secure/path/to/velero-credentials
```

The file uses the provider's expected credential format; don't echo it to logs.
For a secret already provisioned by External Secrets or another manager, use its
name in values and skip imperative creation. Add the cluster values file to a
new ConfigMap in `flux/clusters/iximiuz-platform/velero/kustomization.yaml`:

```yaml
configMapGenerator:
- name: velero-cluster-values
  namespace: velero
  files:
  - values.yaml
  options:
    labels:
      reconcile.fluxcd.io/watch: Enabled
generatorOptions:
  disableNameSuffixHash: true
```

The shared Velero template already references optional `velero-cluster-values`.
Generating this ConfigMap is enough: its values merge after the shared defaults,
with no HelmRelease patch required. Keep the stable name and watch label above.

Build the resulting overlay. The platform already selects Velero with normal
reconciliation; no suspension flag needs changing. Commit/push configuration,
excluding credentials, and reconcile:

```sh
kustomize build flux/clusters/iximiuz-platform/velero
flux reconcile source git flux-system --timeout=2m
flux reconcile kustomization flux-system --timeout=2m
flux reconcile kustomization velero --timeout=15m
kubectl -n velero rollout status deployment/velero --timeout=5m
kubectl -n velero get backupstoragelocations
velero backup-location get
```

Expect the storage location Available. Inspect server logs and provider errors if
not. A Ready server/HelmRelease does not prove the bucket is writable or data is
recoverable. No automatic schedule is supplied.

## Metadata smoke backup and isolated restore

```sh
kubectl apply -f flux/infrastructure/backup/velero/backup-metadata.example.yaml
velero backup describe application-metadata-smoke --details
velero backup logs application-metadata-smoke
```

Wait for Completed, investigate warnings/errors and independently confirm objects
exist in the external bucket. This example covers only demo/application namespace
objects; snapshots and file-system backup are disabled, so PVC data is not copied.
Use disposable application objects and restore into separate namespaces:

```sh
velero restore create application-metadata-smoke-restore \
  --from-backup application-metadata-smoke \
  --namespace-mappings demo:demo-restore,applications:applications-restore \
  --wait
velero restore describe application-metadata-smoke-restore --details
```

Review resource names/selectors, namespace references, quotas, external dependencies
and current admission policies before doing this. Namespace remapping does not
rewrite every application's embedded namespace reference. Do not test restore by
overwriting live databases, namespaces or the control plane. Define success using
actual recovered application behavior, not merely a Completed status.

Plan application-consistent PostgreSQL/OpenBao backups and PVC data movement
separately. Test restoration after losing the original storage before claiming
protection from playground destruction. Protect root signing/unseal material with
an independent custody process.

## Pause or uninstall

Flux suspension stops reconciliation, not running Velero or existing schedules.
Suspend schedules explicitly when required. Review backup object and bucket
retention before removing the release/CRDs; `cleanUpCRDs` must remain false.
Revoking provider credentials stops future access but does not erase backups.
