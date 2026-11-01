# Central platform namespaces

`namespaces.yaml` is the single namespace-definition bundle for all
infrastructure templates. Its 18 namespace objects include `ai`, `ci`, `proxy`,
`quality`, `velero`, `tetragon` and `trivy-system`. The Tetragon privileged and
Trivy baseline Pod Security labels are preserved. No individual resource
folder contains a namespace.yaml or creates a namespace implicitly.

Select this directory once in foundation, before workload/controller templates.
The existing full-platform foundation already does so. The bundle creates
namespaces only: selecting it does not install optional charts or add-ons.
The Kubernetes `kube-system` and Flux bootstrap `flux-system` namespaces remain
owned by their respective bootstraps.

For a standalone lab, apply the bundle before applying a template:

```sh
kubectl apply -k flux/infrastructure/namespaces
```

For an existing installation, migrate namespace ownership before reconciling
old workload inventories that prune. Reconcile foundation first and confirm
namespace reconciliation labels identify foundation before removing an old
owner's namespace inventory. Do not blindly prune or delete an existing
namespace as part of moving its manifest. Namespace deletion deletes workloads
and data in that namespace. No live ownership migration is performed by this
repository-only refactor; all prior playgrounds were already destroyed.
