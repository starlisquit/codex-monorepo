# RBAC primitives

The base creates only ServiceAccount `application`, with API token automount
disabled. It grants no permissions. Optional objects are Kustomize Components:

| Component under `opt-in/` | Object | Effect when selected |
| --- | --- | --- |
| `cluster-role` | ClusterRole `application-pod-reader` | Defines get/list/watch on Pods only; grants nothing without a binding |
| `role-binding` | RoleBinding `application-pod-reader` | Grants that ClusterRole inside the consuming namespace |
| `cluster-role-binding` | ClusterRoleBinding `application-pod-reader` | Grants that ClusterRole across all namespaces |

The namespaced RoleBinding deliberately reuses a ClusterRole; a RoleBinding can
limit a ClusterRole's namespaced permissions to one namespace. Select
`cluster-role` plus one binding, or supply a matching existing role. No Secret,
exec, log, write, wildcard or admin permissions are granted by these examples.
Patch rules deliberately for the application's actual needs. Add a separate
Role template later if role definitions must also be namespaced.

For `flux/clusters/<run>/app-identity/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: demo
namePrefix: api-
resources:
- ../../../infrastructure/primitives/rbac
components:
- ../../../infrastructure/primitives/rbac/opt-in/cluster-role
- ../../../infrastructure/primitives/rbac/opt-in/role-binding
```

Choose and provision the namespace separately. This produces ServiceAccount
`api-application` and ClusterRole/RoleBinding `api-application-pod-reader`.
Built-in Kustomize references transform roleRef and subject names; the subject's
`default` namespace placeholder is replaced by the wrapper namespace. Always
set `namespace` in the wrapper; building without it targets `default`. A
ClusterRole and ClusterRoleBinding are cluster-scoped; their metadata remains
without a namespace. Use a unique namePrefix per application/namespace to avoid
cross-overlay ownership collisions. Keep roleRef stable after creation because
Kubernetes makes it immutable.

For explicitly required cluster-wide Pod reading, substitute
`opt-in/cluster-role-binding` for `opt-in/role-binding`. Do not include both
bindings merely for convenience. Selecting only the ClusterRole grants no access.

Set the consuming Pod's `serviceAccountName` to the resulting account name.
The Deployment and CronJob starters also disable token automount at Pod level;
applications calling the API must explicitly enable it there (or supply a scoped
projected token). Changing the ServiceAccount setting alone cannot override a
Pod's `automountServiceAccountToken: false`.

Composition checks verify namespaced and cluster-scoped bindings, renamed
references and transformed subject namespaces. Live authorization has not been
tested. After deployment, use `kubectl auth can-i --as=system:serviceaccount:demo:api-application`
for the intended verbs/resources and namespace; confirm disallowed operations
and cross-namespace access remain denied for a namespaced binding.
