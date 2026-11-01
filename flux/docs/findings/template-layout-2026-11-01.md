# Template-local opt-ins and central namespaces — 2026-11-01

Optional additions now live under their owning resource's `opt-in/` directory.
All individual `namespace.yaml` files have been removed from the templates;
`infrastructure/namespaces/namespaces.yaml` is the single namespace-definition
bundle. No live cluster deployment or ownership migration was performed.

## Opt-in layout

Paths below are relative to `flux/infrastructure`:

| Addition | New location | How it is selected |
| --- | --- | --- |
| Cilium bootstrap mode | networking/cilium/opt-in/bootstrap | Kustomize components |
| ESO OpenBao store | secrets/external-secrets/opt-in/openbao-store | Kustomize resources, after controllers/backend |
| OpenBao verification ExternalSecret | secrets/external-secrets/opt-in/openbao-verification | Separate Kustomize resources, with the store |
| Ceph write/read verification | storage/rook-ceph/cluster/opt-in/verification | Separate Kustomize resources after Ceph/CSI |
| LiteLLM PostgreSQL values example | ai/litellm/opt-in/postgresql/values.example.yaml | Configure and copy to cluster-owned values |
| Velero S3 values example | backup/velero/opt-in/s3/values.example.yaml | Configure and copy to cluster-owned values |
| Velero metadata-only smoke Backup | backup/velero/opt-in/backup-metadata | Explicit Kustomization after storage configuration |
| KEDA ScaledObject example | autoscaling/keda/opt-in/scaledobject/scaledobject.yaml.example | Replace placeholders and select a copied manifest |
| Additional Prometheus datasource example | observability/datasources/opt-in/prometheus/prometheus.yaml.example | Configure endpoint and select a copied manifest |

There is no top-level `flux/components` directory. The Cilium bootstrap object
still uses the native Kustomize Component kind and `components` field; only its
location changed. Ordinary resources retain the Kustomization kind and are
selected through `resources`. No parent implicitly enables its opt-ins. Values
files are Helm configuration, not Kubernetes resources; placeholder examples
remain excluded rather than becoming automatically deployed objects.

Both Cilium cluster consumers, the secret-store and storage-check consumers,
READMEs, runbooks and current documentation links have been updated. Standalone
verification/test fixture inputs remain under `runbooks/examples`, rather than
being mixed into production templates. Primary deployable template directories
and required PKI bundles remain ordinary templates, not nested optional extras.

## Namespace consolidation

Removed 11 resource-local namespace files, including duplicated ci, ui, broker
and demo declarations. The central bundle contains 18 unique namespaces. It
preserves `tetragon`'s privileged and `trivy-system`'s baseline Pod Security
labels. Chart namespace fields remain unchanged; they target a namespace and
do not create it.

Foundation already selects the central bundle. Standalone template deployment
now requires selecting/applying this bundle first; each former namespace-owning
template's README documents the prerequisite. The Kubernetes `kube-system` and
Flux bootstrap `flux-system` namespaces remain managed by their bootstraps.
Selecting the bundle creates namespaces only and does not enable optional charts.

The full-platform selection previously already included 14 unique namespaces.
It now includes the four additional central definitions ai, ci, proxy and
quality. Every previous selected object, including the security namespaces and
their labels, is unchanged. Duplicate namespace declarations from standalone
templates no longer give the demo namespace multiple intended owners.

On an existing live installation, moving namespace ownership requires ordering:
reconcile/adopt the central foundation namespaces before allowing former
workload inventories to prune their namespace entries. Confirm the intended
foundation reconciliation owner first; do not delete namespaces to accomplish
a manifest move. Namespace deletion can delete all contained resources. The
repo's previous playgrounds were already destroyed; this refactor performs no
live migration or deletion. See the namespace bundle README for that contract.

## Verification

- Passed all **104 Kustomize builds**, existing 37 Flux child definitions and
  25 HelmRelease coverage/dependency gates.
- Updated validation to build Components through consuming Kustomizations,
  rather than attempting an unsupported standalone Component build. Both
  Cilium consumers still exercise bootstrap mode; its default template keeps
  its normal dependency list.
- Before/after full-platform comparison: 142 selected unique identities became
  146. The only additions are Namespace/ai, ci, proxy and quality. No previous
  objects were removed or changed.
- Independently compared all 11 affected standalone templates against the
  previous commit: their non-Namespace objects are identical, and none emits
  its own Namespace anymore.
- Asserted 18 unique central namespace objects, no individual namespace.yaml
  files and no infrastructure Namespace object outside the central bundle.
- Confirmed default Cilium, ESO, Ceph cluster and Velero outputs do not include
  their opt-in mode/resources. The optional Velero Backup has its own explicit
  build; examples requiring configuration remain excluded.
- Scanned references for removed paths and checked whitespace. No chart versions,
  Helm values, TLS connection settings, credentials or resource sizing changed.

[Sanitized comparison evidence](evidence/template-layout-2026-11-01.json) records
the counts and identity comparison. These are offline render checks, not a new
end-to-end installation claim. No playground was created or retained.
