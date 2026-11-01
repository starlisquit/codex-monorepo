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
| VictoriaTraces agent | ServiceMonitor and configured VTSingle remoteWrite destination |
| Flux Operator | Operator metrics ServiceMonitor (UI is bundled in the same chart) |
| KEDA | Operator, metrics adapter, and admission-webhook ServiceMonitors; workload scaling can query the VM API |
| OpenTelemetry Demo | SDK metrics via VMAgent; OTLP logs via VLAgent; OTLP traces via VTAgent; Collector retained for protocol compatibility |
| Blackbox Exporter | Exporter self-monitoring and a probe of the existing VictoriaMetrics `/health` endpoint |

Rook creates Ceph and CSI runtime resources after reconciliation; their service
existence, labels, and target health must be checked in the running cluster.
The Headlamp chart does not provide an application metrics exporter switch. No nonexistent metrics endpoint or additional application is
introduced for them. Optional features such as Cilium ClusterMesh are not enabled
just to collect their metrics. Empty alert-rule and dashboard flags are not needed
for ingestion; collection uses one ServiceMonitor, PodMonitor, or native VM scrape
route per endpoint rather than enabling competing scrape mechanisms.

## OpenBao

OpenBao uses three HA replicas with integrated Raft storage and a 10Gi
`ceph-block` persistent volume per replica. Standalone mode is disabled, and no
Consul backend is configured. The server configuration is a structured YAML object that the chart renders as
JSON. `server.ha.config: {}` selects the chart's JSON-rendering branch, including
for Raft; keep it as an object when editing `server.ha.raft.config`. Raft peers retry joining through the chart's `openbao-active`
Service after a leader has been initialized and unsealed.

Initialization, unsealing, and Raft snapshots remain operational steps: initialize
one replica only, securely retain its recovery/unseal material, and unseal the
replicas as required. Do not initialize each replica as a separate cluster.
Retry-join does not provide auto-unseal. Take and test Raft snapshot backups;
replication is not a substitute for backups. Create the `ceph-block` StorageClass
before deploying, or adjust the storage class and capacity for your cluster.

The server enables Prometheus retention and unauthenticated access to its metrics
endpoint; other API operations still require authentication. Access uses HTTPS
with certificate verification. The existing CA Issuer `openbao-injector-ca` signs
both the injector and server certificates; its historical name does not restrict
it to the injector.

The `openbao-server` Certificate creates `openbao-server-tls`. Its certificate
covers the OpenBao Service names, individual Raft pods through wildcard internal
Service DNS names, and loopback IPs for local CLI/readiness checks. Names assume
the `openbao` release, `secrets` namespace, and `cluster.local` domain; update them
when changing those settings.

The server mounts its TLS Secret read-only, enables TLS on its listener, and uses
`BAO_CACERT` for local CLI trust. Raft retry-join uses HTTPS and the mounted CA.
The advertised API address uses each pod's internal DNS name rather than its
uncertified dynamic IP. The server ServiceMonitor verifies the same CA and the
active Service DNS name. OpenBao still needs initialization and unsealing before
normal telemetry is available.

The injector's own webhook/metrics certificate remains `openbao-injector-tls`.
Its webhook trust bundle is maintained by cert-manager CA injection, and its
ServiceMonitor verifies that certificate. A Helm post-render patch additionally
passes the server CA from `openbao-server-tls/ca.crt` through the pinned injector's
`AGENT_INJECT_VAULT_CACERT_BYTES` setting. This supplies CA trust to injected agents
without copying the server private key or requiring a TLS Secret in each workload
namespace. Workloads can still override injection settings, so keep their TLS
annotations aligned with this configuration.

A second Helm post-render patch replaces the chart's default readiness command,
which skips TLS verification, with `bao status` using the mounted CA. Apply the
component through its HelmRelease to retain these patches. For a manual Helm
install or local rendering, apply the same post-render patches; chart values alone
do not contain them.

OpenBao depends on cert-manager and the monitoring CRDs. Certificate issuance,
handshakes, and renewal behavior require live-cluster validation. After certificate
renewal, arrange a controlled OpenBao TLS reload. CA rotation also requires
refreshing the injector environment and reinjecting/restarting workloads that
received the old CA. Existing workloads and external clients must trust the CA
before switching them to HTTPS. Never copy a CA or server private key to clients.

## Validation and deployment checks

All chart renders use a Kubernetes 1.35 validation profile with the monitoring CRDs
advertised to Helm. Cilium's API address uses a test-only override during
rendering. The traces agent now uses the configured VTSingle destination. Monitors
are checked against the pinned CRD schemas and static Service port references.
The structured OpenBao Raft configuration is checked against the rendered JSON,
StatefulSet, and persistent volume settings.

After deployment, inspect the converted VM scrape resources and VMAgent's targets
and verify recent samples for each component. Certificate issuance, OpenBao
initialization/unseal, exporter connectivity, runtime Ceph/CSI services, namespace
access, and network policies still require live-cluster validation. Network
policies are owned by each consuming cluster; permit the actual metrics ports
when restricting access to infrastructure namespaces.

## Full OpenTelemetry demo

The [demo](infrastructure/demo/opentelemetry-demo/README.md) emits SDK metrics,
logs, and traces. Its Collector bridges the official SDKs' protocol requirements
and forwards through native VMAgent, VLAgent, and VTAgent rather than directly to
storage. Span-to-metrics conversion and the associated dashboard are removed.
VLAgent is enabled in push mode within the existing VM stack, with Kubernetes log
tailing disabled. VLSingle, VTSingle, and their Grafana datasources remain enabled.
