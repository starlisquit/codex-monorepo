# Flux infrastructure templates

This directory follows the requested infrastructure layout, with the
CloudNativePG operator and an example PostgreSQL instance in separate directories.
Shared components reconcile when included; cluster-specific overlays select,
configure, and order them. The full lab overlay is `clusters/iximiuz-platform/`; its desired
state does not imply that every workload has completed live verification.

Start with the [documentation index](docs/README.md) and follow the
[bootstrap runbooks](runbooks/README.md). The docs record verified findings and
unfinished work separately, including the paused API slowness investigation.

## Layout

- `infrastructure/backup/velero/`: Velero with an excluded S3 configuration example; no backup protection until storage and credentials are configured.
- `infrastructure/security/`: Tetragon runtime telemetry and Trivy Operator reports with monitoring.
- `docs/`: architecture, deployment findings, and operational responsibilities.
- `runbooks/`: exact bootstrap/verification/recovery steps and checked-in helper scripts.
- `policies/`: reusable admission and network policies; individual policies document their scope and Audit/Deny behavior.
- `dashboards/`: reusable GrafanaDashboard CRs for the minimal demo, capacity, and scrape health.
- `clusters/`: separate minimal and full-platform cluster overlays.
- `infrastructure/sources/`: shared Helm repositories and OCI chart sources.
- `infrastructure/storage/rook-ceph/csi-drivers/`: CSI Driver CRs via the separate chart; the operator chart alone does not deploy the driver workloads.
- Each chart directory contains a HelmRelease, `values.yaml`, and a Kustomize build.
- `databases/cloudnative-pg/operator/`: PostgreSQL operator release.
- `databases/cloudnative-pg/clusters/application/`: example managed PostgreSQL cluster.
- `observability/dashboards/`: category subfolders, each with a starter
  `overview.yaml` and its own `kustomization.yaml`. Add more dashboard files to
  a category and list them in that category's Kustomization.
- `observability/datasources/`: additional GrafanaDatasource resources and an
  excluded example; the VM chart retains ownership of its default datasources.
- `observability/metrics-server/`: Kubernetes Metrics API for `kubectl top` and resource-based autoscaling, alongside VictoriaMetrics.
- `observability/prometheus-operator-crds/`: monitoring CRDs only; see
  [monitoring setup](MONITORING.md) for collection and dependency details.
- `ui/flux-ui/`: standalone Flux Web UI; Flux is bootstrapped separately, without
  the Flux Operator managing its lifecycle.
- `autoscaling/keda/`: KEDA monitoring and an excluded VictoriaMetrics scaling example.
- `demo/opentelemetry-demo/`: two standalone official demo services (currency and quote), with no automatic traffic; telemetry is
  routed through native VM agents, with a Collector for SDK protocol compatibility.
- `ui/headlamp/`: Kubernetes web UI with its own HelmRelease.
- `policy/kyverno/`: Kyverno engine; reusable policies live in `flux/policies/`.
- `ci/gitlab-runner/`: official GitLab Runner chart, one manager and five concurrent jobs by default.
- `ci/renovate/`: official Renovate CronJob, explicit GitLab repository scope and initial dry-run mode.
- `quality/sonarqube/`: official SonarSource chart with Community Build, external PostgreSQL and persistent data.

The CI/quality templates require their documented credential Secrets and, for
SonarQube, a database. They are opt-in components for consuming cluster overlays;
adding them does not enable them in the full-platform cluster. Validate them in
focused playgrounds rather than deploying unrelated infrastructure.

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
5. Select components through cluster Kustomizations. Shared HelmReleases reconcile
   by default when included; use dependency and health gates for deployment order.
   Omit unneeded components rather than shipping them suspended. Explicit suspension
   remains an operator action for maintenance, not a resource-sizing workaround.

Source references assume Flux permits cross-namespace references. If your Flux
installation disables them, place the source resources alongside their releases
and adjust the references instead.

## Dependencies and cluster configuration

Use separate Flux Kustomizations with `dependsOn` and HelmRelease health checks:

- Rook/CSI operator -> separate CSI driver chart + Ceph cluster/pool -> PVC write/read check -> storage consumers.
- CloudNativePG operator + ready storage -> PostgreSQL instance.
- Grafana Operator -> VictoriaMetrics stack (creates Grafana CRs) -> dashboards.
- Kyverno -> any policies defined by the consuming cluster.
- cert-manager -> trust-manager; its trust namespace is explicitly `certificates`.

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

The single `victoria-metrics-k8s-stack` release enables its operator-managed
VictoriaLogs and VictoriaTraces backends for OpenTelemetry signals. Each
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

The initial template validation rendered the original 20 pinned charts using a
Kubernetes 1.35 profile. Live deployment subsequently exposed additional runtime
requirements and a Helm 4 Collector rendering failure that the Helm 3 render did
not catch. See [deployment findings](docs/findings/deployment-findings.md).

The current local validation covers 67 Kustomize builds, the platform dependency
DAG and storage gates, and syntax checks for the runbook helpers. The updated charts (Rook operator,
CSI drivers, trust-manager, demo, and Metrics Server) also render under Helm 3
and Helm 4.0.0. Run:

```sh
flux/runbooks/scripts/validate.sh
```

Build success does not establish live readiness, sustainable capacity, backup
recoverability, or end-to-end demo telemetry. The full stack uses explicit
readiness gates; its demo rollout and the current API slowness diagnosis remain
unfinished at the time of this documentation update.

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
| metrics-server | `3.14.0` |
| victoria-metrics-k8s-stack | `0.97.0` |
| victoria-traces-agent | `0.2.1` |
| kyverno | `3.9.2` |
| external-secrets | `2.14.0` |
| openbao | `0.30.6` |
| rook-ceph-cluster | `1.21.1` |
| rook-ceph | `1.21.1` |
| ceph-csi-drivers | `1.1.0` |
| grafana-operator | `5.25.0` |
| headlamp | `0.46.0` |
| prometheus-operator-crds | `32.0.2` |
| flux-operator | `0.62.1` |
| keda | `2.21.0` |
| opentelemetry-demo | `0.42.6` |
| gitlab-runner | `0.94.2` |
| sonarqube | `2026.5.1003` |
| renovate | `46.396.0` |
