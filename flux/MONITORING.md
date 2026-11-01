# Metrics collection into VictoriaMetrics

Metrics endpoints and their collection resources are enabled for the configured
components. The HelmReleases remain suspended; these manifests do not establish
live ingestion until the components are installed and their targets are healthy.

## Collection path and installation order

1. Install `observability/prometheus-operator-crds` (chart `32.0.2`, verified
   2026-11-01). This installs monitoring resource definitions only, with no
   Prometheus server or Prometheus Operator.
2. Install Grafana Operator, then the VM stack. The VM operator's Prometheus
   converter is explicitly enabled. It converts ServiceMonitors and PodMonitors
   into VMServiceScrapes and VMPodScrapes.
3. VMAgent has `selectAllByDefault: true` and discovers native scrape resources
   across namespaces. Do not restrict operator watch scope or VMAgent selectors
   without adding equivalent namespace access and selectors.
4. Install the remaining components. HelmRelease dependencies ensure monitoring
   CRDs exist before chart-generated monitors are installed. Raw resources, such
   as the PostgreSQL instance PodMonitor, also need a Flux Kustomization dependency
   on the ready CRD release and their application operator.

Existing node exporter, kube-state-metrics, Grafana, and VM component collection
continues through the VM stack's built-in native scrape integrations.

## Enabled integrations

| Component | Metrics collection |
| --- | --- |
| Cilium | Agent, operator, and Envoy ServiceMonitors |
| Hubble | DNS, drop, TCP, flow, ICMP, HTTPv2 metrics; metrics and Relay ServiceMonitors |
| NATS | Prometheus exporter and PodMonitor |
| Valkey | Exporter, metrics Service, and ServiceMonitor |
| CloudNativePG | Operator PodMonitor plus a separate `application-db` PodMonitor |
| Rook/Ceph | Operator metrics Service/ServiceMonitor, chart CSI monitor, and CephCluster monitoring |
| cert-manager / trust-manager | Metrics endpoints and ServiceMonitors |
| Kyverno | Metrics Services and ServiceMonitors for admission, background, cleanup, and reports controllers |
| External Secrets | Metrics Services and ServiceMonitors for the controller, webhook, and certificate controller |
| OpenBao | Server telemetry and ServiceMonitor, plus injector metrics and a separate ServiceMonitor |
| Grafana Operator | ServiceMonitor |
| VictoriaTraces agent | ServiceMonitor; a real remoteWrite destination is still required |
| Flux Operator | Operator metrics ServiceMonitor (UI is bundled in the same chart) |
| KEDA | Operator, metrics adapter, and admission-webhook ServiceMonitors; workload scaling can query the VM API |
| Blackbox Exporter | Exporter self-monitoring and a probe of the existing VictoriaMetrics `/health` endpoint |

Rook creates Ceph and CSI runtime resources after reconciliation; their service
existence, labels, and target health must be checked in the running cluster.
The Headlamp and Kyverno-policies charts do not provide an application metrics
exporter switch. No nonexistent metrics endpoint or additional application is
introduced for them. Optional features such as Cilium ClusterMesh are not enabled
just to collect their metrics. Empty alert-rule and dashboard flags are not needed
for ingestion; collection uses one ServiceMonitor, PodMonitor, or native VM scrape
route per endpoint rather than enabling competing scrape mechanisms.

## OpenBao

OpenBao uses three HA replicas with integrated Raft storage and a 10Gi
`ceph-block` persistent volume per replica. Standalone mode is disabled, and no
Consul backend is configured. The single HCL configuration uses a readable YAML
literal block. Raft peers retry joining through the chart's `openbao-active`
Service after a leader has been initialized and unsealed.

Initialization, unsealing, and Raft snapshots remain operational steps: initialize
one replica only, securely retain its recovery/unseal material, and unseal the
replicas as required. Do not initialize each replica as a separate cluster.
Retry-join does not provide auto-unseal. Take and test Raft snapshot backups;
replication is not a substitute for backups. Create the `ceph-block` StorageClass
before deploying, or adjust the storage class and capacity for your cluster.

The server enables Prometheus retention and unauthenticated access to its metrics
endpoint. Other API operations still require authentication. The existing server
listener remains HTTP (`tls_disable = 1`); the injector certificate described below
does not secure it. Configure server TLS and adapt the Raft join URL, client trust,
and monitoring scheme before production. The server must be initialized and
unsealed before normal telemetry is available.

The injector's metrics share its HTTPS webhook listener. Its chart extraObjects
create a namespaced cert-manager CA and serving certificate. A CA-injection
annotation keeps the webhook trust bundle in sync. The injector ServiceMonitor
trusts `ca.crt` from `openbao-injector-tls` and checks the service DNS name; TLS
verification is enabled. OpenBao therefore depends on the ready cert-manager
release as well as monitoring CRDs. Keep serving certificate DNS names, Secret
references, and monitor selectors aligned if renaming the OpenBao release.

## Validation and deployment checks

All chart renders use a Kubernetes 1.35 validation profile with the monitoring CRDs
advertised to Helm. Cilium's API address and the traces agent's remoteWrite URL use
test-only overrides during rendering, not committed destination values. Monitors
are checked against the pinned CRD schemas and static Service port references.
The single OpenBao Raft HCL configuration is parsed and checked against the
rendered StatefulSet and persistent volume settings.

After deployment, inspect the converted VM scrape resources and VMAgent's targets
and verify recent samples for each component. Certificate issuance, OpenBao
initialization/unseal, exporter connectivity, runtime Ceph/CSI services, namespace
access, and network policies still require live-cluster validation. The existing
application network-policy examples cover only port 9090; adapt them to the actual
metrics ports before extending default deny to infrastructure namespaces.
