# Kubernetes primitives

Small, independently selectable Kustomize templates for application workloads.
These use native Kubernetes APIs and require no Helm source. There is no root
Kustomization that deploys everything. Consumers choose a namespace separately.
Optional objects live in the owning primitive's `opt-in/` folder.

Available: [`deployment`](deployment), with an optional internal HTTP Service.

## Candidates to add next

| Primitive | Use | Useful opt-ins |
| --- | --- | --- |
| Job | Migrations, one-off tasks; bounded retries and deadline | ServiceAccount, secret references |
| CronJob | Scheduled tasks; explicit timezone and overlap policy | History/cleanup settings |
| StatefulSet | Stateful applications without a suitable operator | Headless Service, PVC templates |
| DaemonSet | One agent per eligible node | Node selectors, tolerations; explicit privileges if necessary |
| Service | Independent ClusterIP, headless or external service selection | Additional ports |
| HTTPRoute | HTTP routing through an existing Gateway | TLS-related filters, timeouts |
| HorizontalPodAutoscaler | Scale workloads using resource/custom metrics | Behavior policies; metrics prerequisites |
| PodDisruptionBudget | Bound voluntary disruption | Workload-specific availability policy |
| NetworkPolicy | Explicit application ingress/egress | DNS and approved dependency rules |
| ServiceAccount and RBAC | Workload identity and minimum permissions | Explicit API access rules |
| ConfigMap and Secret references | Runtime configuration without committed credentials | ExternalSecret integration when its CRDs exist |
| PersistentVolumeClaim | Independently managed persistent storage | Storage class and capacity overrides |

Start with Job and CronJob, then NetworkPolicy, HPA and PDB. Keep lifecycle and
policy primitives separate so consumers can choose what fits each workload.
Prefer existing database operators over a generic StatefulSet for supported
databases. Configuration containing secret values belongs in the established
secret-management workflow, not a reusable manifest.
