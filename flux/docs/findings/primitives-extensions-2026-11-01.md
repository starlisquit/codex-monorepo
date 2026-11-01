# CronJob, Gateway and RBAC primitives — 2026-11-01

Implemented the next primitives without enabling them in any completed run.
Standalone HPA is excluded; autoscaling remains with KEDA.

## Added templates

- `infrastructure/primitives/cronjob`: daily 03:00 Europe/Istanbul task;
  Forbid scheduled overlap, bounded retries/deadlines/history/TTL, non-root
  read-only container and no mounted API token. BusyBox is a replaceable starter.
- `infrastructure/primitives/gateway`: Gateway plus individually selectable
  HTTPRoute, GRPCRoute, TLSRoute, TCPRoute and UDPRoute components under `opt-in`.
  Components add their required listeners; HTTPRoute uses the base HTTP listener.
  Parent/backend references follow Kustomize name transformations.
- `infrastructure/primitives/rbac`: ServiceAccount only by default, without
  permissions; opt-in ClusterRole, RoleBinding and ClusterRoleBinding. The example
  role grants only get/list/watch Pods. A RoleBinding scopes that ClusterRole to
  its namespace; the cluster-wide binding is a separate explicit selection.
- `infrastructure/networking/gateway-api-crds/opt-in/experimental-routes`:
  official Gateway API v1.4.0 TLSRoute, TCPRoute and UDPRoute CRDs, separate from
  the existing Standard-channel CRDs. TLSRoute uses storage version v1alpha3;
  TCPRoute/UDPRoute use v1alpha2. No duplicate standard CRDs are included.

## Validation

- Repository validation passed: **137 Kustomize builds**, plus existing run
  source/namespace readiness coverage and dependency DAG checks.
- Rendered each Gateway route component individually and all five together.
  All six combinations passed the official vendored v1.4.0 CRD schemas.
  Checked unique listeners, route attachment to the matching allowed kind,
  namespace transformation, prefixed Gateway parent references and prefixed
  backend Service references when the Service is in the same build.
- Composed each RBAC binding with the ServiceAccount and ClusterRole. Checked
  matching transformed roleRef/subject names and subject namespace. ClusterRole
  and ClusterRoleBinding metadata remained cluster-scoped. Default RBAC build
  contained only the ServiceAccount; default Gateway build contained no routes.
- Rendered CronJob and RBAC objects passed Kubernetes v1.34.0 standalone strict
  JSON schemas from `yannh/kubernetes-json-schema` (schema checks only).
- [Evidence and vendored file checksums](evidence/primitives-extensions-2026-11-01.json).

No playground was created. CronJob execution, live RBAC authorization and actual
protocol traffic have not been tested for these templates. CRD schema acceptance
does not establish Gateway controller support: choose a compatible implementation
for each protocol, check status conditions and send real traffic. Default class
`cilium` is configurable and is not a support claim for every route type.

Consumer READMEs describe namespace selection, workloads/backends, credentials,
TLS and authorization prerequisites. No namespace, backend workload, credential,
admin role, GatewayClass or Gateway controller is implicitly created. KEDA remains
the autoscaling entry point; there is no standalone HPA template.
