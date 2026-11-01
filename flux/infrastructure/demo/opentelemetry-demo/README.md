# OpenTelemetry observability demo

Official chart `opentelemetry-demo` is pinned to `0.42.6` (application `3.1.0`,
Collector `0.160.0`), verified on 2026-11-01. The release remains suspended until
explicitly enabled. This component creates the `demo` namespace.

## Telemetry paths

```text
Instrumented demo services + generated traffic
  └─ OTLP → demo/otel-collector
       ├─ SDK metrics + span-derived metrics → Prometheus endpoint :9464
       │    └─ ServiceMonitor → VM operator → VMAgent → VictoriaMetrics
       ├─ logs → VictoriaLogs OTLP HTTP endpoint
       └─ traces → VictoriaTraces OTLP HTTP endpoint
```

SDK metric, log, and trace exporters are explicitly set to OTLP, with a 10-second
metric export interval and cumulative metric temporality. Existing per-component
instrumentation and exporters shipped by the official chart are retained. The
load generator autostarts with five users. Optional GenAI examples retain their
upstream recorded-fixture configuration; no external model API key is supplied.

The Collector's span-metrics connector retains gRPC attributes (`rpc.system`,
`rpc.system.name`, `rpc.service`, `rpc.method`, and status-code attributes). This
produces metrics that can distinguish gRPC calls, unlike Hubble's general HTTP/2
metrics alone. Application instrumentation must actually populate those attributes;
SDKs differ in their RPC semantic-convention versions.

One Collector deployment avoids multiple independent span-metrics aggregators.
Host, kubelet, and cluster metric presets are disabled because the VM stack
already collects platform metrics. The chart's demo dependency scraping and
Kubernetes metadata enrichment remain enabled. The Collector's own telemetry
also flows through its configured OTLP metrics/logs pipeline.

Bundled Prometheus, Grafana, Jaeger, and OpenSearch are disabled. The existing VM
stack now enables its operator-managed VLSingle and VTSingle components, each with
seven-day retention and a 10Gi `ceph-block` volume. Its bundled Grafana installs the
VictoriaMetrics/VictoriaLogs datasource plugins, and Grafana Operator provisions
VictoriaMetrics, VictoriaLogs, and VictoriaTraces datasources.

The demo sends traces directly to VTSingle's OTLP endpoint. The separate existing
VictoriaTraces agent is optional for this path; it now also has a real VTSingle
remoteWrite destination if enabled.

## Install and view

1. Prepare Rook/Ceph and the `ceph-block` StorageClass, monitoring CRDs, Grafana
   Operator, and the VM stack. Unsuspend the selected releases intentionally.
2. Verify that VLSingle/VTSingle are Ready and their services exist. The VM stack
   HelmRelease depends on Ceph; the demo release depends on the VM stack and
   monitoring CRDs. A HelmRelease becoming Ready does not by itself prove that
   every operator-created backend is ready.
3. Reconcile shared sources and this directory using your cluster's Flux
   Kustomizations. The demo Kustomization should depend on ready Grafana Operator
   CRDs as well, because it includes a GrafanaDashboard.
4. Unsuspend `demo/opentelemetry-demo` and wait for its workloads and Collector.

The upstream app is substantial: this render contains 26 workload controllers,
with container memory limits totaling 6,904Mi before adding VM backends or other
platform services. Reserve suitable capacity (at least roughly 8Gi spare RAM for
the demo itself), plus capacity for logs/traces storage and the existing stack.
Review scheduling and resource requirements for your cluster before enabling it.

For local storefront access:

```sh
kubectl -n demo port-forward service/frontend-proxy 8080:8080
```

The bundled backend UI proxy paths are not used; access the existing platform
Grafana instead. Find **OpenTelemetry Demo / Overview** for span and gRPC call
rates. It selects the platform Grafana across namespaces and uses the existing
`VictoriaMetrics` datasource UID. Allow at least a couple of scrape intervals
before rate panels populate.

In Grafana Explore, use **VictoriaLogs (DS)** for application logs and
**VictoriaTraces** for traces. Trace IDs emitted in logs can help navigate between
them; automatic cross-datasource linking is not configured. Do not expose the
demo or load-generator UI publicly without adding the required access controls.
No ingress, Gateway, or example workload policies are introduced here.

If your cluster enforces namespace isolation, permit demo OTLP traffic to the
Collector, VMAgent scraping of TCP 9464, Collector logs/traces egress to
`observability` on TCP 9428/10428, and Kubernetes API/required demo-service traffic.
Adjust names and URLs when changing release names, namespaces, or cluster domain.

## Validation performed

- Helm renders of the demo, expanded VM stack, and configured traces agent.
- Generated full Collector config validated by the checksum-verified upstream
  Collector `0.160.0` binary.
- A local Collector smoke test accepted synthetic OTLP metrics, logs, and gRPC
  spans; emitted an increasing `traces_span_metrics_calls_total` counter with RPC
  labels and application metrics; and forwarded nonempty log/trace OTLP payloads
  to local capture servers using the configured Victoria ingestion paths.
- Kustomize builds and custom-resource schema/reference checks.

The local smoke test verifies Collector processing and routing, not ingestion by
live Victoria backends. No Kubernetes deployment, real load test, or live Grafana
import has been performed. All HelmReleases remain suspended.

References:

- [Official demo chart](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-demo)
- [VictoriaLogs OTLP ingestion](https://docs.victoriametrics.com/victorialogs/data-ingestion/opentelemetry/)
- [VictoriaTraces OTLP ingestion](https://docs.victoriametrics.com/victoriatraces/data-ingestion/opentelemetry/)
