# Flux infrastructure templates

This directory follows the requested infrastructure layout, with the
CloudNativePG operator and an example PostgreSQL instance in separate directories.
It is a starting scaffold, not a deployment-ready cluster configuration.

## Layout

- `infrastructure/sources/`: shared Helm repositories and the Grafana Operator OCI source.
- Each chart directory contains a HelmRelease, `values.yaml`, and a Kustomize build.
- `databases/cloudnative-pg/operator/`: PostgreSQL operator release.
- `databases/cloudnative-pg/clusters/application/`: example managed PostgreSQL cluster.
- `observability/dashboards/`: category subfolders, each with a starter
  `overview.yaml` and its own `kustomization.yaml`. Add more dashboard files to
  a category and list them in that category's Kustomization.
- `observability/datasources/`: additional GrafanaDatasource resources and an
  excluded example; the VM chart retains ownership of its default datasources.
- `observability/prometheus-operator-crds/`: monitoring CRDs only; see
  [monitoring setup](MONITORING.md) for collection and dependency details.
- `gitops/flux-operator/`: Flux Operator, its bundled Web UI, and a FluxInstance;
  see its README for operator-first bootstrap on a new cluster.
- `autoscaling/keda/`: KEDA monitoring and an excluded VictoriaMetrics scaling example.
- `demo/opentelemetry-demo/`: official demo application and generated traffic
  routed through native VM agents, with a Collector for SDK protocol compatibility.
- `ui/headlamp/`: Kubernetes web UI with its own suspended HelmRelease.
- `policy/kyverno/`: Kyverno engine only; each cluster defines its own policies.

## Before enabling a release

1. Chart versions are pinned to the latest stable releases verified on
   2026-11-01 (see the table below). Review Kubernetes compatibility and the
   supported chart values before enabling any release.
2. Create the target namespaces: `observability`, `rook-ceph`, `databases`,
   `kyverno`, `certificates`, `secrets`, `broker`, `ui`, `autoscaling`, and `applications` as needed.
   The demo component creates its own `demo` namespace.
   Cilium targets the existing `kube-system` namespace; sources use `flux-system`.
3. Build the desired component with `kustomize build <component-directory>`.
   Kustomize generates a stable values ConfigMap; `valuesFrom` connects it to
   the HelmRelease. The watch label tells Flux to reconcile values changes.
4. Create cluster-specific Flux Kustomizations pointing to the selected component
   directories. Use `sourceRef` for your bootstrapped GitRepository, and readiness
   checks for HelmReleases. There is deliberately no top-level deployment that
   enables every component.
5. Remove `spec.suspend: true` from only the releases you intend to install.
   Suspension applies to HelmReleases, not raw PostgreSQL or dashboard
   resources: include those directories only when their prerequisites are ready.

Source references assume Flux permits cross-namespace references. If your Flux
installation disables them, place the source resources alongside their releases
and adjust the references instead.

## Dependencies and cluster configuration

Use separate Flux Kustomizations with `dependsOn` and HelmRelease health checks:

- Rook operator -> Ceph cluster -> workloads requiring persistent volumes.
- CloudNativePG operator + ready storage -> PostgreSQL instance.
- Grafana Operator -> VictoriaMetrics stack (creates Grafana CRs) -> dashboards.
- Kyverno -> any policies defined by the consuming cluster.
- cert-manager -> trust-manager.

`kustomization.yaml` files assemble manifests; they do not enforce controller
readiness or installation order.

Configure Cilium for the cluster's API endpoint, IPAM, and Gateway API CRDs
before installation. Kube-proxy replacement, Hubble, Relay, UI, and Gateway API
are enabled. Set `k8sServiceHost` and `k8sServicePort` to a real API endpoint
reachable without kube-proxy; do not use the Kubernetes Service IP. CNI
installation or replacement requires a cluster-specific rollout plan. Envoy, L7
proxy/configuration, opt-in service load balancing, and Gateway HTTP/2 protocol
support are explicitly enabled; see [Cilium mesh and gRPC notes](infrastructure/networking/cilium/README.md).

Rook intentionally has no selected disks. Configure nodes, unused devices, Ceph
replication, RBD/CephFS StorageClasses, and RGW explicitly using the pinned chart.
The PostgreSQL and NATS examples reference `ceph-block`; create that StorageClass
or change the examples. Other chart values default to `{}` until configured.
In particular, configure persistence, resources, high availability, credentials,
and exposure according to the selected chart version. OpenBao uses three HA Raft replicas with persistent storage; initialization,
unseal, backups, and authentication still need configuration (see
[monitoring and OpenBao notes](MONITORING.md)). External Secrets needs
a configured SecretStore or ClusterSecretStore.

The single `victoria-metrics-k8s-stack` release now enables its operator-managed
VictoriaLogs and VictoriaTraces backends for the full OpenTelemetry demo. Each
uses a 10Gi `ceph-block` volume with seven-day retention. The existing traces agent
is configured to forward to that VictoriaTraces backend; the demo Collector routes
all telemetry through VMAgent, VLAgent, and VTAgent. See the [demo guide](infrastructure/demo/opentelemetry-demo/README.md).

The stack's bundled Grafana remains enabled. Its `extraObjects` creates an external
Grafana Operator binding named `platform`, labeled `dashboards: platform`, pointing
to the bundled Grafana Service and generated admin credential Secret. No credential
values are committed. If you configure an existing admin Secret later, update the
binding's Secret references too.

Both `defaultDashboards.grafanaOperator.enabled` and
`defaultDatasources.grafanaOperator.enabled` are enabled, with matching instance
selectors. Grafana sidecars are disabled so the operator owns dashboard/datasource
provisioning. `grafana.forceDeployDatasource` keeps datasource CR generation enabled
when the datasource sidecar is off. Install Grafana Operator and its CRDs first;
configure the stack's Flux Kustomization to depend on the operator's ready release.
The chart's sync job creates the default GrafanaDashboard resources at runtime.

Custom starter dashboards also select `dashboards: platform` and use the
`VictoriaMetrics` datasource. Their metric queries depend on the installed
exporters and versions. They do not install exporters or scraping resources.

## PostgreSQL example

`application-db` contains three instances, a 20Gi volume per instance, and an
`application` database owned by `application`. CloudNativePG generates the
`application-db-app` credential Secret. Clients in the same namespace use
`application-db-rw`; other namespaces use
`application-db-rw.databases.svc`.

Patch replicas, resources, storage, and the PostgreSQL image per environment.
Before production, configure off-cluster backups and test restores. Replicas
do not replace backups. Keep database reconciliation separate, consider Flux
`prune: false`, and define a deliberate deletion and data-retention procedure.
Never commit plaintext credentials.

## Policies

Only the Kyverno engine is provided. Admission and network policies are owned by
the consuming cluster; no example policy resources or bundled policy chart are
included under `infrastructure/policy/`.

## Validation

All 32 Kustomize builds and all 20 pinned Helm charts were rendered successfully
using a Kubernetes 1.35 validation profile. Cilium used a test-only API endpoint,
which is not saved in these manifests. The traces agent now has a real VTSingle
remoteWrite destination. The Grafana and GrafanaDatasource
resources were also validated against the pinned Grafana Operator CRD schemas.

Run `kustomize build` for each directory containing `kustomization.yaml`.
Check Kubernetes compatibility and render again with your actual cluster settings
before deployment. Helm rendering does not establish live readiness or validate
the chart's runtime dashboard sync job. No cluster has been bootstrapped or
reconciled by adding these templates.

## Pinned chart versions

Verified against official Helm indexes and the Grafana Operator stable release
and OCI artifact on 2026-11-01. Prerelease and deprecated chart entries were excluded.
These are chart versions, not application image versions.

| Chart | Version |
| --- | --- |
| nats | `2.15.2` |
| cert-manager | `v1.21.3` |
| trust-manager | `v0.26.0` |
| cloudnative-pg | `0.29.1` |
| valkey | `0.12.1` |
| cilium | `1.20.4` |
| prometheus-blackbox-exporter | `11.20.2` |
| victoria-metrics-k8s-stack | `0.97.0` |
| victoria-traces-agent | `0.2.1` |
| kyverno | `3.9.2` |
| external-secrets | `2.14.0` |
| openbao | `0.30.6` |
| rook-ceph-cluster | `1.21.1` |
| rook-ceph | `1.21.1` |
| grafana-operator | `5.25.0` |
| headlamp | `0.46.0` |
| prometheus-operator-crds | `32.0.2` |
| flux-operator | `0.62.1` |
| keda | `2.21.0` |
| opentelemetry-demo | `0.42.6` |
