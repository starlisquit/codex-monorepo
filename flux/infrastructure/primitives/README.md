# Kubernetes primitives

Small, independently selectable Kustomize templates for application workloads.
Workload and RBAC templates use built-in APIs; Gateway templates require the
Gateway API CRDs and a compatible controller. No Helm source is required. There is no root
Kustomization that deploys everything. Consumers choose a namespace separately.
Optional objects live in the owning primitive's `opt-in/` folder.

Available:

- [`deployment`](deployment): stateless HTTP workload, optional internal Service.
- [`cronjob`](cronjob): scheduled task with bounded retries and runtime.
- [`gateway`](gateway): Gateway with individually selectable HTTP, gRPC, TLS,
  TCP and UDP routes/listeners.
- [`rbac`](rbac): ServiceAccount with independently selectable ClusterRole,
  RoleBinding and ClusterRoleBinding.

## Candidates to add next

| Primitive | Use | Useful opt-ins |
| --- | --- | --- |
| Job | Migrations, one-off tasks; bounded retries and deadline | ServiceAccount, secret references |
| StatefulSet | Stateful applications without a suitable operator | Headless Service, PVC templates |
| DaemonSet | One agent per eligible node | Node selectors, tolerations; explicit privileges if necessary |
| Service | Independent ClusterIP, headless or external service selection | Additional ports |
| PodDisruptionBudget | Bound voluntary disruption | Workload-specific availability policy |
| NetworkPolicy | Explicit application ingress/egress | DNS and approved dependency rules |
| ConfigMap and Secret references | Runtime configuration without committed credentials | ExternalSecret integration when its CRDs exist |
| PersistentVolumeClaim | Independently managed persistent storage | Storage class and capacity overrides |

Autoscaling belongs to the existing KEDA templates; no standalone HPA primitive
is planned. Add Job next, then NetworkPolicy and PDB. Keep lifecycle and
policy primitives separate so consumers can choose what fits each workload.
Prefer existing database operators over a generic StatefulSet for supported
databases. Configuration containing secret values belongs in the established
secret-management workflow, not a reusable manifest.
