# Flux infrastructure templates

This directory follows the requested infrastructure layout, with the
CloudNativePG operator and an example PostgreSQL instance in separate directories.
It is a starting scaffold, not a deployment-ready cluster configuration.

## Layout

- `infrastructure/sources/`: shared Helm repositories and the Grafana Operator OCI source.
- Each chart directory contains a HelmRelease, `values.yaml`, and a Kustomize build.
- `databases/cloudnative-pg/operator/`: PostgreSQL operator release.
- `databases/cloudnative-pg/clusters/application/`: example managed PostgreSQL cluster.
- `observability/dashboards/`: starter GrafanaDashboard resources with one panel each.
- `policy/cluster-policies/`: example Kyverno policies in Audit mode, scoped to `applications`.
- `policy/network-policies/`: example policies scoped to `applications`.

## Before enabling a release

1. Pin every chart version. The `*` selectors are intentionally unpinned template
   values; replace them with reviewed exact versions, including the OCI source.
   Check each version's supported values before enabling it.
2. Create the target namespaces: `observability`, `rook-ceph`, `databases`,
   `kyverno`, `certificates`, `secrets`, `broker`, and `applications` as needed.
   Cilium targets the existing `kube-system` namespace; sources use `flux-system`.
3. Build the desired component with `kustomize build <component-directory>`.
   Kustomize generates a stable values ConfigMap; `valuesFrom` connects it to
   the HelmRelease. The watch label tells Flux to reconcile values changes.
4. Create cluster-specific Flux Kustomizations pointing to the selected component
   directories. Use `sourceRef` for your bootstrapped GitRepository, and readiness
   checks for HelmReleases. There is deliberately no top-level deployment that
   enables every component.
5. Remove `spec.suspend: true` from only the releases you intend to install.
   Suspension applies to HelmReleases, not raw PostgreSQL, dashboard, or policy
   resources: include those directories only when their prerequisites are ready.

Source references assume Flux permits cross-namespace references. If your Flux
installation disables them, place the source resources alongside their releases
and adjust the references instead.

## Dependencies and cluster configuration

Use separate Flux Kustomizations with `dependsOn` and HelmRelease health checks:

- Rook operator -> Ceph cluster -> workloads requiring persistent volumes.
- CloudNativePG operator + ready storage -> PostgreSQL instance.
- Grafana Operator + configured Grafana instance -> dashboards.
- Kyverno -> Kyverno policies and custom ClusterPolicies.
- cert-manager -> trust-manager.

`kustomization.yaml` files assemble manifests; they do not enforce controller
readiness or installation order.

Configure Cilium for the cluster's API endpoint, IPAM, kube-proxy mode, and
Gateway API CRDs before installation. CNI installation or replacement requires
a cluster-specific rollout plan. Hubble and Gateway API are enabled in its values.

Rook intentionally has no selected disks. Configure nodes, unused devices, Ceph
replication, RBD/CephFS StorageClasses, and RGW explicitly using the pinned chart.
The PostgreSQL and NATS examples reference `ceph-block`; create that StorageClass
or change the examples. Other chart values default to `{}` until configured.
In particular, configure persistence, resources, high availability, credentials,
and exposure according to the selected chart version. OpenBao needs an explicit
initialization, unseal, storage, and authentication design; External Secrets needs
a configured SecretStore or ClusterSecretStore.

The original single `victoria-metrics-k8s-stack` release is retained. Its presence
does not imply that VictoriaLogs, VLAgent, or VictoriaTraces servers are installed;
check the selected chart's contents. Configure the requested traces agent's
destination explicitly. No separate logs or traces server releases are included.

The stack's Grafana is enabled. To use Grafana Operator dashboards with it, add an
operator-supported external Grafana resource with secure credentials and the label
`dashboards: platform`. Configure a Prometheus-compatible Grafana datasource named
`VictoriaMetrics`. Starter dashboard metrics depend on installed exporters and
their metric naming; adjust queries to match your versions. Dashboard definitions
do not install exporters, scraping resources, or datasources.

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

## Policy examples

Review policies before including them. Kyverno examples start in Audit mode.
The resource policy requires CPU/memory requests and memory limits; CPU limits
can be added according to your workload policy. The privileged-container example
covers regular containers; use the reviewed Kyverno policy library for complete
coverage of init containers, ephemeral containers, and other security controls.

Network policies enforce immediately when applied. The default deny blocks both
ingress and egress in `applications`. The DNS example assumes kube-dns labels;
adjust it for NodeLocal DNS if used. Ingress assumes a controller namespace named
`networking` and application port 8080; monitoring assumes port 9090. Adjust these
selectors and ports for Cilium/Gateway traffic and actual application metrics.
The OpenBao allowance assumes its standard pod label and TCP port 8200.
Add explicit allowances for PostgreSQL, Valkey, NATS, application dependencies,
and required external destinations before enabling default deny.

## Validation

Run `kustomize build` for each directory containing `kustomization.yaml`.
Rendered manifests must additionally be checked against your selected chart
versions and Kubernetes/CRD schemas before deployment. No cluster has been
bootstrapped or reconciled by adding these templates.
