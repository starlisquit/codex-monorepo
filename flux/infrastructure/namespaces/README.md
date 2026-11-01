# Individually selectable namespaces

Namespace definitions are centralized here, with one Kustomize base per
namespace. Select only the ones a deployment needs, for example
`infrastructure/namespaces/ai`. No workload template contains a namespace.yaml.
The Tetragon privileged and Trivy baseline Pod Security labels are retained in
their respective namespace bases.

The root Kustomization remains an optional convenience bundle containing all
18 namespaces. It is not required and run foundations select only their needed namespace bases. The Kubernetes
kube-system and Flux bootstrap flux-system namespaces remain bootstrap-owned.

A small installation can provision just AI's namespace:

```sh
kubectl apply -k flux/infrastructure/namespaces/ai
```

Or select the namespace base alongside its source and workload template in a
consuming Kustomization. If multiple releases share a namespace, select it once
under a common foundation owner, rather than repeating it in every consumer.

For existing installations, review ownership and pruning before deselecting a
namespace: deleting a namespace deletes its contents. This repository refactor
performs no live migration or deletion. Reconcile intended namespace ownership
before permitting an old owner to prune its inventory.
